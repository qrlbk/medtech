"""Search index management and autocomplete (Meilisearch + DB fallback).

Lexical search / autocomplete is served by Meilisearch (typo tolerance,
ru/kk morphology). If Meilisearch is unavailable, we fall back to a Postgres
trigram search so the feature never hard-fails.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ServiceCatalog, ServiceSynonym
from app.services import cache

logger = logging.getLogger(__name__)

INDEX_NAME = "services"
_client = None
_failed = False


def _get_client():
    global _client, _failed
    if _client is not None or _failed:
        return _client
    try:
        import meilisearch

        _client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
        _client.health()
    except Exception as exc:  # noqa: BLE001 - search engine optional
        logger.warning("Meilisearch unavailable (%s); using DB fallback.", exc)
        _failed = True
        _client = None
    return _client


def reindex_all(db: Session) -> int:
    """Push catalog services (with synonyms) into the Meilisearch index."""
    client = _get_client()
    services = list(db.scalars(select(ServiceCatalog)))
    syn_map: dict[str, list[str]] = {}
    for cid, alias in db.execute(
        select(ServiceSynonym.catalog_id, ServiceSynonym.alias)
    ).all():
        syn_map.setdefault(str(cid), []).append(alias)

    docs = [
        {
            "id": str(s.id),
            "name": s.name_norm,
            "category": s.category.value,
            "synonyms": syn_map.get(str(s.id), []),
        }
        for s in services
    ]
    cache.invalidate("autocomplete:")
    if client is None:
        return 0
    index = client.index(INDEX_NAME)
    index.update_searchable_attributes(["name", "synonyms"])
    index.update_filterable_attributes(["category"])
    index.add_documents(docs)
    logger.info("Indexed %d services in Meilisearch", len(docs))
    return len(docs)


def autocomplete(db: Session, query: str, limit: int = 8) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []

    cache_key = f"autocomplete:{query.lower()}:{limit}"
    cached = cache.get_json(cache_key)
    if cached is not None:
        return cached

    client = _get_client()
    if client is not None:
        try:
            res = client.index(INDEX_NAME).search(query, {"limit": limit})
            hits = [
                {"id": h["id"], "name": h["name"], "category": h["category"]}
                for h in res["hits"]
            ]
            cache.set_json(cache_key, hits)
            return hits
        except Exception as exc:  # noqa: BLE001
            logger.warning("Meili search failed, falling back: %s", exc)

    hits = _db_autocomplete(db, query, limit)
    cache.set_json(cache_key, hits)
    return hits


def _db_autocomplete(db: Session, query: str, limit: int) -> list[dict]:
    """Trigram-similarity fallback over catalog names and synonyms."""
    similarity = func.similarity(ServiceCatalog.name_norm, query)
    rows = db.execute(
        select(ServiceCatalog.id, ServiceCatalog.name_norm, ServiceCatalog.category)
        .where(
            (ServiceCatalog.name_norm.ilike(f"%{query}%")) | (similarity > 0.2)
        )
        .order_by(similarity.desc())
        .limit(limit)
    ).all()
    return [
        {"id": str(cid), "name": name, "category": cat.value}
        for cid, name, cat in rows
    ]
