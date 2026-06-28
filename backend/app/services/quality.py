"""Data-quality checks: price validation, currency conversion, anomaly detection.

Implements ТЗ correctness requirements: validate prices, convert USD->KZT,
flag implausible values and sudden jumps.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import settings

# Static fallback rate; a real deployment would refresh from the NB RK API.
USD_TO_KZT = 475.0

# Plausible KZT bounds for a single medical service line item.
MIN_PRICE_KZT = 100.0
MAX_PRICE_KZT = 3_000_000.0

# A price change beyond this factor vs. the previous value is flagged.
ANOMALY_FACTOR = 10.0


@dataclass(slots=True)
class PriceCheck:
    ok: bool
    price_kzt: float | None
    reason: str = ""


def to_kzt(price: float | None, currency: str) -> float | None:
    if price is None:
        return None
    if currency == "USD":
        return round(price * USD_TO_KZT, 2)
    return float(price)


def validate_price(price: float | None, currency: str) -> PriceCheck:
    if price is None:
        return PriceCheck(False, None, "no_price")
    if price <= 0:
        return PriceCheck(False, None, "non_positive")
    kzt = to_kzt(price, currency)
    if kzt is None:
        return PriceCheck(False, None, "conversion_failed")
    if kzt < MIN_PRICE_KZT:
        return PriceCheck(False, kzt, "below_min")
    if kzt > MAX_PRICE_KZT:
        return PriceCheck(False, kzt, "above_max")
    return PriceCheck(True, kzt)


def is_anomalous(new_price: float, prev_price: float | None,
                 factor: float = ANOMALY_FACTOR) -> bool:
    """True if the new price differs from the previous by more than `factor`x."""
    if prev_price is None or prev_price <= 0:
        return False
    ratio = new_price / prev_price
    return ratio >= factor or ratio <= 1 / factor


def is_fresh(parsed_at: datetime, fresh_days: int | None = None) -> bool:
    """A price is "fresh" (shown as actual) if parsed within DATA_FRESH_DAYS (ТЗ)."""
    fresh_days = fresh_days or settings.data_fresh_days
    if parsed_at.tzinfo is None:
        parsed_at = parsed_at.replace(tzinfo=UTC)
    return parsed_at >= datetime.now(UTC) - timedelta(days=fresh_days)


def cleanup_old_raw(db: Session, retention_days: int | None = None) -> int:
    """Delete raw_documents older than RAW_RETENTION_DAYS (>=90 per ТЗ audit rule)."""
    from app.models import RawDocument

    retention_days = retention_days or settings.raw_retention_days
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    result = db.execute(delete(RawDocument).where(RawDocument.fetched_at < cutoff))
    db.commit()
    return result.rowcount or 0
