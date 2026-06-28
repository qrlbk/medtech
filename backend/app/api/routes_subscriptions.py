"""Price-drop subscriptions (authenticated users)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import PriceSubscription, User
from app.schemas.auth import SubscriptionIn, SubscriptionOut

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[SubscriptionOut])
def list_subscriptions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(PriceSubscription).where(PriceSubscription.user_id == user.id)
    ).all()
    return [
        SubscriptionOut(
            id=s.id, service_id=s.service_id, clinic_id=s.clinic_id,
            target_price_kzt=float(s.target_price_kzt) if s.target_price_kzt else None,
        )
        for s in rows
    ]


@router.post("", response_model=SubscriptionOut)
def create_subscription(
    payload: SubscriptionIn, user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = PriceSubscription(
        user_id=user.id, service_id=payload.service_id, clinic_id=payload.clinic_id,
        target_price_kzt=payload.target_price_kzt,
    )
    db.add(sub)
    db.commit()
    return SubscriptionOut(
        id=sub.id, service_id=sub.service_id, clinic_id=sub.clinic_id,
        target_price_kzt=payload.target_price_kzt,
    )


@router.patch("/me/telegram")
def link_telegram(
    chat_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Link a Telegram chat id so the user receives price-drop alerts."""
    user.telegram_chat_id = chat_id
    db.commit()
    return {"status": "linked"}


@router.delete("/{subscription_id}", status_code=204)
def delete_subscription(
    subscription_id: uuid.UUID, user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.get(PriceSubscription, subscription_id)
    if sub is None or sub.user_id != user.id:
        raise HTTPException(404, "Subscription not found")
    db.delete(sub)
    db.commit()
