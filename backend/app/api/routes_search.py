"""Search and autocomplete endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.enums import ServiceCategory
from app.schemas.common import SearchResponse, ServiceSuggestion
from app.services import search as search_svc
from app.services import serving

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/autocomplete", response_model=list[ServiceSuggestion])
def autocomplete(
    q: str = Query(..., min_length=1), limit: int = Query(8, le=20),
    db: Session = Depends(get_db),
):
    return search_svc.autocomplete(db, q, limit)


@router.get("", response_model=SearchResponse)
def search(
    service_id: uuid.UUID,
    city: str | None = None,
    category: ServiceCategory | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    has_online_booking: bool | None = None,
    sort: str = Query("price_asc"),
    lat: float | None = None,
    lon: float | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    service = serving.get_service(db, service_id)
    if service is None:
        raise HTTPException(404, "Service not found")
    filters = serving.PriceFilters(
        city=city, category=category, min_price=min_price, max_price=max_price,
        min_rating=min_rating, has_online_booking=has_online_booking,
    )
    results = serving.search_prices(
        db, service_id, filters, sort=sort, lat=lat, lon=lon, limit=limit, offset=offset
    )
    analytics = serving.service_analytics(db, service_id, city)
    return {
        "service": {"id": service.id, "name": service.name_norm,
                    "category": service.category},
        "count": len(results),
        "results": results,
        "analytics": analytics,
    }
