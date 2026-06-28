"""Service catalog, clinic card, price history, analytics endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import ServiceCatalog
from app.models.enums import ServiceCategory
from app.schemas.common import Analytics, ServiceOut
from app.services import serving

router = APIRouter(tags=["catalog"])


@router.get("/services", response_model=list[ServiceOut])
def list_services(
    category: ServiceCategory | None = None, db: Session = Depends(get_db)
):
    stmt = select(ServiceCatalog)
    if category:
        stmt = stmt.where(ServiceCatalog.category == category)
    rows = db.scalars(stmt.order_by(ServiceCatalog.name_norm)).all()
    return [{"id": s.id, "name": s.name_norm, "category": s.category} for s in rows]


@router.get("/services/{service_id}/analytics", response_model=Analytics)
def analytics(service_id: uuid.UUID, city: str | None = None, db: Session = Depends(get_db)):
    return serving.service_analytics(db, service_id, city)


@router.get("/clinics/{clinic_id}")
def clinic_card(clinic_id: uuid.UUID, db: Session = Depends(get_db)):
    card = serving.get_clinic_card(db, clinic_id)
    if card is None:
        raise HTTPException(404, "Clinic not found")
    return card


@router.get("/prices/history")
def price_history(clinic_id: uuid.UUID, service_id: uuid.UUID, db: Session = Depends(get_db)):
    return serving.price_history(db, clinic_id, service_id)
