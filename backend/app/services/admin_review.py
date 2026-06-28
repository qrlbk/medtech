"""Human-in-the-loop resolution of the unmatched queue.

When a reviewer confirms a match, the raw service name is (optionally) saved
as a new synonym, so the matcher learns and future runs auto-match it.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ParsedOffer,
    ServiceCatalog,
    ServiceSynonym,
    UnmatchedQueue,
)
from app.models.enums import MatchStatus
from app.services import cache
from app.services.clinics import get_or_create_clinic
from app.services.normalization import upsert_price
from app.services.quality import validate_price
from app.services.text import normalize_text


def list_unmatched(db: Session, limit: int = 50, offset: int = 0) -> list[dict]:
    rows = db.execute(
        select(UnmatchedQueue, ParsedOffer, ServiceCatalog.name_norm)
        .join(ParsedOffer, ParsedOffer.id == UnmatchedQueue.parsed_offer_id)
        .outerjoin(ServiceCatalog, ServiceCatalog.id == UnmatchedQueue.suggested_catalog_id)
        .where(UnmatchedQueue.resolved.is_(False))
        .order_by(UnmatchedQueue.score.desc().nullslast())
        .limit(limit).offset(offset)
    ).all()
    return [
        {
            "id": q.id,
            "parsed_offer_id": o.id,
            "service_name_raw": o.service_name_raw,
            "source": o.source,
            "clinic_raw": o.clinic_raw,
            "city": o.city,
            "price_raw": float(o.price_raw) if o.price_raw is not None else None,
            "suggested_catalog_id": q.suggested_catalog_id,
            "suggested_name": suggested_name,
            "score": q.score,
        }
        for q, o, suggested_name in rows
    ]


def resolve(
    db: Session, queue_id: uuid.UUID, catalog_id: uuid.UUID | None,
    add_as_synonym: bool = True,
) -> bool:
    item = db.get(UnmatchedQueue, queue_id)
    if item is None:
        return False
    offer = db.get(ParsedOffer, item.parsed_offer_id)
    if offer is None:
        return False

    # Reject: not a real service.
    if catalog_id is None:
        offer.match_status = MatchStatus.rejected
        item.resolved = True
        db.commit()
        return True

    service = db.get(ServiceCatalog, catalog_id)
    if service is None:
        return False

    if add_as_synonym:
        alias_norm = normalize_text(offer.service_name_raw)
        exists = db.scalar(
            select(ServiceSynonym).where(
                ServiceSynonym.catalog_id == catalog_id,
                ServiceSynonym.alias_norm == alias_norm,
            )
        )
        if exists is None and alias_norm:
            db.add(ServiceSynonym(catalog_id=catalog_id, alias=offer.service_name_raw,
                                  alias_norm=alias_norm, lang="ru"))

    check = validate_price(
        float(offer.price_raw) if offer.price_raw is not None else None,
        offer.currency.value,
    )
    if check.ok:
        clinic = get_or_create_clinic(
            db, offer.clinic_raw or "Неизвестная клиника", offer.city, offer.source_url
        )
        upsert_price(
            db, clinic.id, catalog_id, check.price_kzt,
            parsed_offer_id=offer.id, duration_days=offer.duration_days,
            source_url=offer.source_url, confidence=1.0,
        )

    offer.match_status = MatchStatus.manual
    item.resolved = True
    db.commit()
    cache.invalidate("autocomplete:")
    return True
