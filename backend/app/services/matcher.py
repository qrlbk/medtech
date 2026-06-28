"""Multi-stage service-name matcher.

Pipeline (ordered, first confident hit wins):
  1. exact synonym match
  2. fuzzy/lexical (rapidfuzz)
  3. semantic (pgvector cosine over embeddings)
  4. LLM arbiter for borderline cases (optional)
Anything below threshold returns a suggestion with low score, to be routed
to the human-in-the-loop unmatched queue by the caller.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ServiceCatalog, ServiceEmbedding, ServiceSynonym
from app.services import embeddings
from app.services.llm_arbiter import select_match
from app.services.text import normalize_text

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MatchResult:
    catalog_id: uuid.UUID | None
    score: float
    method: str  # exact | fuzzy | semantic | llm | suggestion | none

    #: Methods that represent a confident, auto-acceptable match.
    CONFIDENT_METHODS = frozenset({"exact", "fuzzy", "semantic", "llm"})

    @property
    def is_confident(self) -> bool:
        return self.catalog_id is not None and self.method in self.CONFIDENT_METHODS


class ServiceMatcher:
    """Stateful matcher that preloads synonyms for fast fuzzy matching."""

    def __init__(self, db: Session) -> None:
        self.db = db
        rows = db.execute(
            select(ServiceSynonym.alias_norm, ServiceSynonym.catalog_id)
        ).all()
        # alias_norm -> catalog_id (exact lookup) and parallel lists for fuzzy.
        self._exact: dict[str, uuid.UUID] = {a: c for a, c in rows}
        self._aliases: list[str] = list(self._exact.keys())
        self._semantic_enabled = embeddings.is_available()

    def match(self, raw_name: str) -> MatchResult:
        norm = normalize_text(raw_name)
        if not norm:
            return MatchResult(None, 0.0, "none")

        # Stage 1: exact synonym.
        if norm in self._exact:
            return MatchResult(self._exact[norm], 1.0, "exact")

        # Stage 2: fuzzy (keep top-K for the LLM fallback).
        fuzzy_ranked = self._fuzzy_ranked(norm, settings.llm_candidate_k)
        fuzzy = fuzzy_ranked[0] if fuzzy_ranked else None
        if fuzzy and fuzzy.score >= settings.normalize_fuzzy_threshold / 100:
            return fuzzy

        # Stage 3: semantic (keep top-K for the LLM fallback).
        semantic_ranked = (
            self._semantic_ranked(raw_name, settings.llm_candidate_k)
            if self._semantic_enabled else []
        )
        semantic = semantic_ranked[0] if semantic_ranked else None
        if semantic and semantic.score >= settings.normalize_match_threshold:
            return semantic

        # Stage 4: LLM selector over the merged lexical + semantic shortlist.
        # Unlike a yes/no verifier, this lets the model pick the right entry from
        # several plausible candidates — essential against a ~1.3k-item catalog.
        if settings.llm_enabled:
            chosen = self._llm_select(raw_name, fuzzy_ranked, semantic_ranked)
            if chosen is not None:
                return chosen

        # Below threshold: return best guess as a non-confident suggestion,
        # so the caller routes it to the human-in-the-loop unmatched queue.
        candidate = self._best_candidate(fuzzy, semantic)
        if candidate and candidate.catalog_id:
            return MatchResult(candidate.catalog_id, candidate.score, "suggestion")
        return MatchResult(None, 0.0, "none")

    def _fuzzy_ranked(self, norm: str, k: int) -> list[MatchResult]:
        """Top-K fuzzy candidates, deduplicated by catalog id (best score wins)."""
        if not self._aliases:
            return []
        hits = process.extract(
            norm, self._aliases, scorer=fuzz.token_set_ratio, limit=max(k * 3, k)
        )
        best: dict[uuid.UUID, float] = {}
        for alias, score, _ in hits:
            cid = self._exact[alias]
            s = score / 100
            if s > best.get(cid, 0.0):
                best[cid] = s
        ranked = sorted(best.items(), key=lambda x: x[1], reverse=True)[:k]
        return [MatchResult(cid, s, "fuzzy") for cid, s in ranked]

    def _semantic_ranked(self, raw_name: str, k: int) -> list[MatchResult]:
        """Top-K semantic candidates by cosine similarity over pgvector."""
        vec = embeddings.embed(raw_name)
        if vec is None:
            return []
        rows = self.db.execute(
            select(
                ServiceEmbedding.catalog_id,
                ServiceEmbedding.embedding.cosine_distance(vec).label("dist"),
            )
            .order_by("dist")
            .limit(k)
        ).all()
        return [MatchResult(cid, 1.0 - float(dist), "semantic") for cid, dist in rows]

    def _llm_select(
        self,
        raw_name: str,
        fuzzy_ranked: list[MatchResult],
        semantic_ranked: list[MatchResult],
    ) -> MatchResult | None:
        """Merge candidate shortlists and let the LLM pick the best (or none)."""
        merged: dict[uuid.UUID, float] = {}
        for r in (*fuzzy_ranked, *semantic_ranked):
            if r.catalog_id is None:
                continue
            if r.score > merged.get(r.catalog_id, 0.0):
                merged[r.catalog_id] = r.score
        if not merged:
            return None

        ranked = sorted(merged.items(), key=lambda x: x[1], reverse=True)
        ranked = ranked[: settings.llm_candidate_k]
        names = {
            s.id: s.name_norm
            for s in self.db.scalars(
                select(ServiceCatalog).where(
                    ServiceCatalog.id.in_([cid for cid, _ in ranked])
                )
            )
        }
        candidates = [(cid, names[cid]) for cid, _ in ranked if cid in names]
        chosen_id = select_match(raw_name, candidates)
        if chosen_id is None:
            return None
        # Confidence: keep the lexical/semantic score but floor it, since the LLM
        # actively endorsed this candidate.
        score = max(merged.get(chosen_id, 0.0), 0.8)
        return MatchResult(chosen_id, score, "llm")

    @staticmethod
    def _best_candidate(*candidates: MatchResult | None) -> MatchResult | None:
        valid = [c for c in candidates if c and c.catalog_id]
        if not valid:
            return None
        return max(valid, key=lambda c: c.score)
