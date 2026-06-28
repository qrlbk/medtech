"""Metadata endpoints: cities, categories, stats, parse-run journal."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import (
    Clinic,
    ParseRun,
    Price,
    ServiceCatalog,
    ServiceSynonym,
    UnmatchedQueue,
)
from app.models.enums import ServiceCategory
from app.schemas.common import StatsOut

router = APIRouter(tags=["meta"])


@router.get("/cities", response_model=list[str])
def cities(db: Session = Depends(get_db)):
    rows = db.scalars(select(distinct(Clinic.city)).order_by(Clinic.city)).all()
    return list(rows)


@router.get("/categories", response_model=list[str])
def categories():
    return [c.value for c in ServiceCategory]


@router.get("/sources", response_model=list[str])
def sources():
    """Slugs of all registered parser sources (for the admin ingest picker)."""
    from parsers.registry import known_sources

    return known_sources()


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    return StatsOut(
        services=db.scalar(select(func.count(ServiceCatalog.id))) or 0,
        synonyms=db.scalar(select(func.count(ServiceSynonym.id))) or 0,
        clinics=db.scalar(select(func.count(Clinic.id))) or 0,
        cities=db.scalar(select(func.count(distinct(Clinic.city)))) or 0,
        active_prices=db.scalar(
            select(func.count(Price.id)).where(Price.is_active.is_(True))
        ) or 0,
        sources=db.scalar(select(func.count(distinct(ParseRun.source)))) or 0,
        unmatched=db.scalar(
            select(func.count(UnmatchedQueue.id)).where(UnmatchedQueue.resolved.is_(False))
        ) or 0,
    )


@router.get("/analytics/market")
def market(city: str | None = None, db: Session = Depends(get_db)):
    from app.services.serving import market_overview

    return market_overview(db, city)


@router.get("/sources/runs")
def source_runs(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ParseRun).order_by(ParseRun.started_at.desc()).limit(limit)
    ).all()
    return [
        {
            "source": r.source, "status": r.status, "offers_found": r.offers_found,
            "offers_new": r.offers_new, "error": r.error,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in rows
    ]
