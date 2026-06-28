"""Gold serving layer: price search, clinic cards, history, analytics.

Powers the public API. Distance sorting uses PostGIS; freshness flags follow
the ТЗ rule (data older than DATA_FRESH_DAYS is not presented as current).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_X, ST_Y, ST_Distance
from sqlalchemy import Float, and_, cast, func, select
from sqlalchemy.orm import Session

from app.models import Clinic, Price, ServiceCatalog
from app.models.enums import ServiceCategory
from app.services.quality import is_fresh


@dataclass(slots=True)
class PriceFilters:
    city: str | None = None
    category: ServiceCategory | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_rating: float | None = None
    has_online_booking: bool | None = None


SORTS = {"price_asc", "price_desc", "updated", "distance"}


def search_prices(
    db: Session,
    service_id: uuid.UUID,
    filters: PriceFilters,
    sort: str = "price_asc",
    lat: float | None = None,
    lon: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return active prices for a service joined with clinic info."""
    has_loc = lat is not None and lon is not None
    point = WKTElement(f"POINT({lon} {lat})", srid=4326) if has_loc else None
    distance_col = (
        ST_Distance(Clinic.geo, point).label("distance_m")
        if point is not None
        else func.cast(None, Float).label("distance_m")
    )

    stmt = (
        select(
            Price.id, Price.price_kzt, Price.duration_days, Price.parsed_at,
            Price.confidence, Price.source_url,
            Clinic.id.label("clinic_id"), Clinic.name.label("clinic_name"),
            Clinic.city, Clinic.address, Clinic.phone, Clinic.working_hours,
            Clinic.website, Clinic.rating, Clinic.has_online_booking,
            ST_Y(cast(Clinic.geo, Geometry)).label("lat"),
            ST_X(cast(Clinic.geo, Geometry)).label("lon"),
            distance_col,
        )
        .join(Clinic, Clinic.id == Price.clinic_id)
        .where(Price.service_id == service_id, Price.is_active.is_(True))
    )

    conditions = []
    if filters.city:
        conditions.append(func.lower(Clinic.city) == filters.city.strip().lower())
    if filters.min_price is not None:
        conditions.append(Price.price_kzt >= filters.min_price)
    if filters.max_price is not None:
        conditions.append(Price.price_kzt <= filters.max_price)
    if filters.min_rating is not None:
        conditions.append(Clinic.rating >= filters.min_rating)
    if filters.has_online_booking is not None:
        conditions.append(Clinic.has_online_booking.is_(filters.has_online_booking))
    if conditions:
        stmt = stmt.where(and_(*conditions))

    if sort == "price_desc":
        stmt = stmt.order_by(Price.price_kzt.desc())
    elif sort == "updated":
        stmt = stmt.order_by(Price.parsed_at.desc())
    elif sort == "distance" and point is not None:
        stmt = stmt.order_by("distance_m")
    else:
        stmt = stmt.order_by(Price.price_kzt.asc())

    stmt = stmt.limit(limit).offset(offset)
    rows = db.execute(stmt).mappings().all()
    return [_serialize_offer(r) for r in rows]


def _serialize_offer(r) -> dict:
    return {
        "price_id": str(r["id"]),
        "price_kzt": float(r["price_kzt"]),
        "duration_days": r["duration_days"],
        "parsed_at": r["parsed_at"].isoformat() if r["parsed_at"] else None,
        "is_fresh": is_fresh(r["parsed_at"]) if r["parsed_at"] else False,
        "confidence": float(r["confidence"]),
        "source_url": r["source_url"],
        "clinic": {
            "id": str(r["clinic_id"]),
            "name": r["clinic_name"],
            "city": r["city"],
            "address": r["address"],
            "phone": r["phone"],
            "working_hours": r["working_hours"],
            "website": r["website"],
            "rating": r["rating"],
            "has_online_booking": r["has_online_booking"],
            "lat": r["lat"],
            "lon": r["lon"],
        },
        "distance_m": float(r["distance_m"]) if r["distance_m"] is not None else None,
    }


def get_service(db: Session, service_id: uuid.UUID) -> ServiceCatalog | None:
    return db.get(ServiceCatalog, service_id)


def get_clinic_card(db: Session, clinic_id: uuid.UUID) -> dict | None:
    clinic = db.get(Clinic, clinic_id)
    if clinic is None:
        return None
    rows = db.execute(
        select(Price.id, Price.price_kzt, Price.parsed_at, Price.duration_days,
               ServiceCatalog.id.label("service_id"), ServiceCatalog.name_norm,
               ServiceCatalog.category)
        .join(ServiceCatalog, ServiceCatalog.id == Price.service_id)
        .where(Price.clinic_id == clinic_id, Price.is_active.is_(True))
        .order_by(ServiceCatalog.category, ServiceCatalog.name_norm)
    ).mappings().all()
    return {
        "id": str(clinic.id),
        "name": clinic.name,
        "city": clinic.city,
        "address": clinic.address,
        "phone": clinic.phone,
        "working_hours": clinic.working_hours,
        "website": clinic.website,
        "rating": clinic.rating,
        "has_online_booking": clinic.has_online_booking,
        "services": [
            {
                "service_id": str(r["service_id"]),
                "name": r["name_norm"],
                "category": r["category"].value,
                "price_kzt": float(r["price_kzt"]),
                "duration_days": r["duration_days"],
                "parsed_at": r["parsed_at"].isoformat() if r["parsed_at"] else None,
            }
            for r in rows
        ],
    }


def price_history(db: Session, clinic_id: uuid.UUID, service_id: uuid.UUID) -> list[dict]:
    """All versioned prices for a (clinic, service) ordered chronologically."""
    rows = db.execute(
        select(Price.price_kzt, Price.parsed_at, Price.is_active)
        .where(Price.clinic_id == clinic_id, Price.service_id == service_id)
        .order_by(Price.parsed_at.asc())
    ).all()
    return [
        {"price_kzt": float(p), "date": d.isoformat() if d else None, "is_active": a}
        for p, d, a in rows
    ]


def market_overview(db: Session, city: str | None = None, limit: int = 10) -> dict:
    """Market-level analytics: per-category coverage and notable services.

    Powers the analytics/insights view. Shows how many services have prices,
    plus the services with the widest price spread (max/min ratio) where a
    user could save the most by comparing.
    """
    cat_stmt = (
        select(ServiceCatalog.category, func.count(func.distinct(Price.service_id)))
        .join(Price, Price.service_id == ServiceCatalog.id)
        .where(Price.is_active.is_(True))
        .group_by(ServiceCatalog.category)
    )
    if city:
        cat_stmt = cat_stmt.join(Clinic, Clinic.id == Price.clinic_id).where(
            func.lower(Clinic.city) == city.strip().lower()
        )
    coverage = {cat.value: count for cat, count in db.execute(cat_stmt).all()}

    spread_stmt = (
        select(
            ServiceCatalog.id, ServiceCatalog.name_norm,
            func.min(Price.price_kzt).label("min_p"),
            func.max(Price.price_kzt).label("max_p"),
            func.count(Price.id).label("n"),
        )
        .join(Price, Price.service_id == ServiceCatalog.id)
        .where(Price.is_active.is_(True))
        .group_by(ServiceCatalog.id, ServiceCatalog.name_norm)
        .having(func.count(Price.id) >= 2)
        .order_by((func.max(Price.price_kzt) / func.min(Price.price_kzt)).desc())
        .limit(limit)
    )
    biggest_savings = [
        {
            "service_id": str(r.id), "name": r.name_norm,
            "min_price": float(r.min_p), "max_price": float(r.max_p),
            "offers": r.n,
            "savings_pct": round((1 - float(r.min_p) / float(r.max_p)) * 100, 1),
        }
        for r in db.execute(spread_stmt).all()
    ]
    return {"coverage_by_category": coverage, "biggest_savings": biggest_savings}


def service_analytics(db: Session, service_id: uuid.UUID, city: str | None = None) -> dict:
    """Market analytics for a service: min/avg/max price and clinic count."""
    stmt = (
        select(
            func.min(Price.price_kzt), func.avg(Price.price_kzt),
            func.max(Price.price_kzt), func.count(Price.id),
        )
        .join(Clinic, Clinic.id == Price.clinic_id)
        .where(Price.service_id == service_id, Price.is_active.is_(True))
    )
    if city:
        stmt = stmt.where(func.lower(Clinic.city) == city.strip().lower())
    pmin, pavg, pmax, count = db.execute(stmt).one()
    return {
        "min_price": float(pmin) if pmin is not None else None,
        "avg_price": round(float(pavg), 2) if pavg is not None else None,
        "max_price": float(pmax) if pmax is not None else None,
        "clinic_count": count,
    }
