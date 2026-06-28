"""Persist raw documents and parsed offers (raw + bronze layers).

Handles de-duplication: re-running a parser must not create duplicate offers
(ТЗ 3.1). Dedup is enforced via ParsedOffer.dedup_hash unique constraint.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ParsedOffer, RawDocument
from app.models.enums import Currency, MatchStatus
from parsers.base import Offer, RawDoc

logger = logging.getLogger(__name__)


def persist_raw_doc(db: Session, doc: RawDoc) -> RawDocument:
    """Insert a raw document unless an identical content_hash already exists."""
    existing = db.scalar(
        select(RawDocument).where(RawDocument.content_hash == doc.content_hash)
    )
    if existing is not None:
        return existing
    row = RawDocument(
        source=doc.source,
        url=doc.url,
        content_type=doc.content_type,
        content_hash=doc.content_hash,
        payload=doc.payload,
    )
    db.add(row)
    db.flush()
    return row


def persist_offers(
    db: Session, offers: list[Offer], raw_doc: RawDocument | None = None
) -> int:
    """Insert new offers, skipping duplicates. Returns count of new rows."""
    if not offers:
        return 0
    incoming = {o.dedup_hash(): o for o in offers}
    existing_hashes = set(
        db.scalars(
            select(ParsedOffer.dedup_hash).where(
                ParsedOffer.dedup_hash.in_(list(incoming.keys()))
            )
        ).all()
    )
    new_count = 0
    for dedup_hash, offer in incoming.items():
        if dedup_hash in existing_hashes:
            continue
        db.add(
            ParsedOffer(
                raw_doc_id=raw_doc.id if raw_doc else None,
                source=offer.source,
                clinic_raw=offer.clinic_raw,
                city=offer.city,
                service_name_raw=offer.service_name_raw,
                price_raw=offer.price_raw,
                currency=Currency(offer.currency),
                duration_days=offer.duration_days,
                source_url=offer.source_url,
                dedup_hash=dedup_hash,
                match_status=MatchStatus.pending,
            )
        )
        new_count += 1
    db.flush()
    return new_count
