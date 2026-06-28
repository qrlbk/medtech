"""Price-drop notifications for subscriptions.

After each pipeline run, checks active subscriptions: if the current best
price for the watched service (optionally a specific clinic) drops to/below
the target or below the last notified value, the user is alerted via Telegram.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.telegram import send_message
from app.models import Price, PriceSubscription, ServiceCatalog, User

logger = logging.getLogger(__name__)


def _current_best(db: Session, service_id, clinic_id) -> float | None:
    stmt = select(Price.price_kzt).where(
        Price.service_id == service_id, Price.is_active.is_(True)
    )
    if clinic_id is not None:
        stmt = stmt.where(Price.clinic_id == clinic_id)
    prices = [float(p) for p in db.scalars(stmt)]
    return min(prices) if prices else None


def check_subscriptions(db: Session) -> int:
    """Returns the number of notifications dispatched."""
    subs = list(db.scalars(select(PriceSubscription)))
    notified = 0
    for sub in subs:
        best = _current_best(db, sub.service_id, sub.clinic_id)
        if best is None:
            continue
        target_ok = sub.target_price_kzt is None or best <= float(sub.target_price_kzt)
        dropped = sub.last_notified_price is None or best < float(sub.last_notified_price)
        if not (target_ok and dropped):
            continue

        user = db.get(User, sub.user_id)
        service = db.get(ServiceCatalog, sub.service_id)
        if user and user.telegram_chat_id and service:
            send_message(
                user.telegram_chat_id,
                f"💰 Цена на «{service.name_norm}» снизилась до {int(best)} ₸.",
            )
        sub.last_notified_price = best
        notified += 1
    db.commit()
    logger.info("Subscription notifications dispatched: %d", notified)
    return notified
