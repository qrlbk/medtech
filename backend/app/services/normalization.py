"""Normalization orchestrator: parsed_offers (bronze) -> prices (silver).

For each pending offer: validate/convert price, match service name to the
catalog (multi-stage), resolve the clinic, and upsert a versioned price.
Low-confidence matches are routed to the human-in-the-loop unmatched queue.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import ParsedOffer, Price, UnmatchedQueue
from app.models.enums import MatchStatus
from app.services.clinics import get_or_create_clinic
from app.services.matcher import ServiceMatcher
from app.services.quality import is_anomalous, validate_price

logger = logging.getLogger(__name__)


@dataclass
class NormalizeStats:
    processed: int = 0
    auto_matched: int = 0
    unmatched: int = 0
    rejected: int = 0
    prices_created: int = 0
    anomalies: int = 0
    reasons: dict[str, int] = field(default_factory=dict)


def upsert_price(
    db: Session,
    clinic_id: uuid.UUID,
    service_id: uuid.UUID,
    price_kzt: float,
    *,
    parsed_offer_id: uuid.UUID,
    duration_days: int | None,
    source_url: str | None,
    confidence: float,
) -> tuple[Price | None, bool]:
    """Insert a new versioned price if changed. Returns (price, anomalous)."""
    current = db.scalar(
        select(Price).where(
            Price.clinic_id == clinic_id,
            Price.service_id == service_id,
            Price.is_active.is_(True),
        )
    )
    if current is not None and float(current.price_kzt) == float(price_kzt):
        # No change: nothing to version.
        return current, False

    anomalous = is_anomalous(price_kzt, float(current.price_kzt) if current else None)

    if current is not None:
        db.execute(
            update(Price).where(Price.id == current.id).values(is_active=False)
        )

    price = Price(
        clinic_id=clinic_id,
        service_id=service_id,
        parsed_offer_id=parsed_offer_id,
        price_kzt=price_kzt,
        duration_days=duration_days,
        source_url=source_url,
        # Anomalous jumps reduce confidence so the UI can flag them.
        confidence=round(confidence * (0.5 if anomalous else 1.0), 3),
        is_active=True,
    )
    db.add(price)
    db.flush()
    return price, anomalous


def normalize_pending(db: Session, limit: int | None = None) -> NormalizeStats:
    matcher = ServiceMatcher(db)
    stats = NormalizeStats()

    query = select(ParsedOffer).where(ParsedOffer.match_status == MatchStatus.pending)
    if limit:
        query = query.limit(limit)
    offers = list(db.scalars(query))

    for offer in offers:
        stats.processed += 1

        check = validate_price(
            float(offer.price_raw) if offer.price_raw is not None else None,
            offer.currency.value,
        )
        if not check.ok:
            offer.match_status = MatchStatus.rejected
            stats.rejected += 1
            stats.reasons[check.reason] = stats.reasons.get(check.reason, 0) + 1
            continue

        result = matcher.match(offer.service_name_raw)

        if not result.is_confident:
            _enqueue_unmatched(db, offer, result.catalog_id, result.score)
            stats.unmatched += 1
            continue

        clinic = get_or_create_clinic(
            db, offer.clinic_raw or "Неизвестная клиника", offer.city, offer.source_url
        )
        price, anomalous = upsert_price(
            db,
            clinic.id,
            result.catalog_id,
            check.price_kzt,
            parsed_offer_id=offer.id,
            duration_days=offer.duration_days,
            source_url=offer.source_url,
            confidence=result.score,
        )
        if price is not None:
            stats.prices_created += 1
        if anomalous:
            stats.anomalies += 1
        # An offer that previously fell into the queue may now match (e.g. after
        # enabling semantic/LLM stages): drop any stale queue entry.
        db.execute(
            delete(UnmatchedQueue).where(UnmatchedQueue.parsed_offer_id == offer.id)
        )
        offer.match_status = MatchStatus.auto
        stats.auto_matched += 1

    db.commit()
    logger.info(
        "Normalized: processed=%d auto=%d unmatched=%d rejected=%d anomalies=%d",
        stats.processed, stats.auto_matched, stats.unmatched, stats.rejected,
        stats.anomalies,
    )
    return stats


def _enqueue_unmatched(
    db: Session, offer: ParsedOffer, suggested: uuid.UUID | None, score: float
) -> None:
    existing = db.scalar(
        select(UnmatchedQueue).where(UnmatchedQueue.parsed_offer_id == offer.id)
    )
    if existing is None:
        db.add(
            UnmatchedQueue(
                parsed_offer_id=offer.id,
                suggested_catalog_id=suggested,
                score=score,
            )
        )
