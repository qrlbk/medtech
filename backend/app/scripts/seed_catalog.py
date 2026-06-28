"""Seed the normalized service catalog from app/data/services_catalog.json.

Idempotent: re-running updates existing entries by normalized name and adds
missing synonyms. Optionally computes pgvector embeddings if the embedding
model is available.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import ServiceCatalog, ServiceEmbedding, ServiceSynonym
from app.models.enums import ServiceCategory
from app.services import embeddings
from app.services.text import normalize_text

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "services_catalog.json"


def seed_catalog(db: Session, with_embeddings: bool = True) -> int:
    entries = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    created = 0
    for entry in entries:
        name = entry["name"]
        category = ServiceCategory(entry["category"])
        svc = db.scalar(select(ServiceCatalog).where(ServiceCatalog.name_norm == name))
        if svc is None:
            svc = ServiceCatalog(name_norm=name, category=category,
                                 description=entry.get("description"))
            db.add(svc)
            db.flush()
            created += 1

        # The canonical name is itself a synonym for matching.
        aliases = [{"alias": name, "lang": "ru"}] + entry.get("synonyms", [])
        existing = {
            s.alias_norm
            for s in db.scalars(
                select(ServiceSynonym).where(ServiceSynonym.catalog_id == svc.id)
            )
        }
        for syn in aliases:
            alias_norm = normalize_text(syn["alias"])
            if not alias_norm or alias_norm in existing:
                continue
            db.add(ServiceSynonym(catalog_id=svc.id, alias=syn["alias"],
                                  alias_norm=alias_norm, lang=syn.get("lang", "ru")))
            existing.add(alias_norm)

    db.flush()

    if with_embeddings and embeddings.is_available():
        backfill_embeddings(db)

    db.commit()
    logger.info("Catalog seeded: %d new services", created)
    return created


def backfill_embeddings(db: Session, batch_size: int = 256) -> int:
    """Compute pgvector embeddings for any catalog services missing them.

    Idempotent and incremental: only embeds rows without an existing vector, so
    it is safe to call after the official catalog import (which adds services
    *after* the initial seed) without recomputing everything. Returns the number
    of services embedded.
    """
    if not embeddings.is_available():
        return 0

    missing = list(
        db.scalars(
            select(ServiceCatalog)
            .outerjoin(ServiceEmbedding, ServiceEmbedding.catalog_id == ServiceCatalog.id)
            .where(ServiceEmbedding.catalog_id.is_(None))
        )
    )
    if not missing:
        return 0

    embedded = 0
    for start in range(0, len(missing), batch_size):
        chunk = missing[start : start + batch_size]
        vectors = embeddings.embed_batch([s.name_norm for s in chunk])
        if vectors is None:
            break
        for svc, vec in zip(chunk, vectors, strict=True):
            db.add(ServiceEmbedding(catalog_id=svc.id, embedding=vec))
        db.flush()
        embedded += len(chunk)

    logger.info("Embeddings backfilled for %d services", embedded)
    return embedded


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as db:
        seed_catalog(db)


if __name__ == "__main__":
    main()
