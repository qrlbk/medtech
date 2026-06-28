"""Embedding service for semantic matching/search.

Two interchangeable providers, chosen via ``settings.embedding_provider``:

* ``local``  — sentence-transformers (offline, free, but pulls torch ~1GB).
* ``openai`` — OpenAI embeddings API (no heavy deps; needs ``OPENAI_API_KEY``).
  Handy when the LLM stack is already configured.

The module degrades gracefully: if the selected provider is unavailable
(package missing, no key, network error) callers get ``None`` and should fall
back to lexical/fuzzy matching only. Remember the embedding dimension
(``settings.embedding_dim``) must match the provider — 384 for the default
MiniLM, 1536 for ``text-embedding-3-small``.
"""
from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)

_model = None
_local_failed = False
_openai_client = None
_openai_failed = False


def _provider() -> str:
    return (settings.embedding_provider or "local").lower()


def _get_local_model():
    global _model, _local_failed
    if _model is not None or _local_failed:
        return _model
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.embedding_model)
    except Exception as exc:  # noqa: BLE001 - optional heavy dependency
        logger.warning("Local embedding model unavailable (%s); semantic disabled.", exc)
        _local_failed = True
        _model = None
    return _model


def _get_openai_client():
    global _openai_client, _openai_failed
    if _openai_client is not None or _openai_failed:
        return _openai_client
    if not settings.openai_api_key:
        logger.warning("OpenAI embeddings selected but OPENAI_API_KEY is empty.")
        _openai_failed = True
        return None
    try:
        from openai import OpenAI

        _openai_client = OpenAI(api_key=settings.openai_api_key)
    except Exception as exc:  # noqa: BLE001 - optional dependency
        logger.warning("OpenAI client unavailable (%s); semantic disabled.", exc)
        _openai_failed = True
        _openai_client = None
    return _openai_client


def is_available() -> bool:
    if not settings.embeddings_enabled:
        return False
    if _provider() == "openai":
        return _get_openai_client() is not None
    return _get_local_model() is not None


def embed(text: str) -> list[float] | None:
    vecs = embed_batch([text])
    return vecs[0] if vecs else None


def embed_batch(texts: list[str]) -> list[list[float]] | None:
    if not settings.embeddings_enabled or not texts:
        return None
    if _provider() == "openai":
        return _embed_openai(texts)
    return _embed_local(texts)


def _embed_local(texts: list[str]) -> list[list[float]] | None:
    model = _get_local_model()
    if model is None:
        return None
    vecs = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vecs]


def _embed_openai(texts: list[str]) -> list[list[float]] | None:
    client = _get_openai_client()
    if client is None:
        return None
    try:
        resp = client.embeddings.create(
            model=settings.embedding_openai_model, input=texts
        )
    except Exception as exc:  # noqa: BLE001 - network/best-effort
        logger.warning("OpenAI embedding call failed: %s", exc)
        return None
    # Preserve request order (API returns objects with an explicit index).
    ordered = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in ordered]
