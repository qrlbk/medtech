"""Re-run normalization on pending offers (e.g. after enabling semantic/LLM).

Backfills any missing catalog embeddings, re-processes offers still in the
``pending`` state through the (now richer) matcher, refreshes the search index,
and prints a before/after summary so the effect of the semantic + LLM stages is
measurable in one command.

Usage:
    python -m app.scripts.renormalize
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.config import settings
from app.db.session import SessionLocal
from app.models import ParsedOffer, Price, UnmatchedQueue
from app.models.enums import MatchStatus
from app.scripts.seed_catalog import backfill_embeddings
from app.services import embeddings
from app.services.normalization import normalize_pending

logger = logging.getLogger(__name__)


def _counts(db) -> dict[str, int]:
    by_status = dict(
        db.execute(
            select(ParsedOffer.match_status, func.count()).group_by(
                ParsedOffer.match_status
            )
        ).all()
    )
    return {
        "pending": by_status.get(MatchStatus.pending, 0),
        "auto": by_status.get(MatchStatus.auto, 0),
        "rejected": by_status.get(MatchStatus.rejected, 0),
        "queue": db.scalar(select(func.count()).select_from(UnmatchedQueue)) or 0,
        "active_prices": db.scalar(
            select(func.count(Price.id)).where(Price.is_active.is_(True))
        )
        or 0,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(
        f"config: provider={settings.embedding_provider} dim={settings.embedding_dim} "
        f"embeddings_enabled={settings.embeddings_enabled} "
        f"embeddings_available={embeddings.is_available()} "
        f"llm_enabled={settings.llm_enabled} llm_model={settings.llm_model}"
    )

    with SessionLocal() as db:
        before = _counts(db)
        print("BEFORE:", before)

        embedded = backfill_embeddings(db)
        db.commit()
        print(f"embeddings backfilled: {embedded}")

        stats = normalize_pending(db)
        print("normalize stats:", stats.__dict__)

        try:
            from app.services.search import reindex_all

            reindex_all(db)
        except Exception as exc:  # noqa: BLE001 - search is optional here
            logger.warning("reindex skipped: %s", exc)

        after = _counts(db)
        print("AFTER:", after)
        print(f"newly auto-matched this run: {after['auto'] - before['auto']}")


if __name__ == "__main__":
    main()
