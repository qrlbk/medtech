"""Clinic resolution: find-or-create a clinic, enriched with seed metadata."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Clinic
from app.services.geo import geocode_clinic

_CLINICS_FILE = Path(__file__).resolve().parent.parent / "data" / "clinics.json"


@lru_cache
def _metadata() -> dict[tuple[str, str], dict]:
    entries = json.loads(_CLINICS_FILE.read_text(encoding="utf-8"))
    return {(e["name"].strip().lower(), e["city"].strip().lower()): e for e in entries}


def get_or_create_clinic(
    db: Session, name: str, city: str | None, source_url: str | None = None
) -> Clinic:
    city = city or "Не указан"
    clinic = db.scalar(
        select(Clinic).where(
            func.lower(Clinic.name) == name.strip().lower(),
            func.lower(Clinic.city) == city.strip().lower(),
        )
    )
    if clinic is not None:
        return clinic

    meta = dict(_metadata().get((name.strip().lower(), city.strip().lower()), {}))
    # Enrich missing geo fields from a live provider (2GIS / Google Maps) when a
    # key is configured; otherwise this is a no-op and the seed data is used.
    if not all(meta.get(k) for k in ("lat", "lon", "address", "working_hours")):
        live = geocode_clinic(name, city)
        if live:
            for key, value in live.items():
                if value is not None and not meta.get(key):
                    meta[key] = value

    geo = None
    if meta.get("lat") is not None and meta.get("lon") is not None:
        geo = WKTElement(f"POINT({meta['lon']} {meta['lat']})", srid=4326)

    clinic = Clinic(
        name=name,
        city=city,
        address=meta.get("address"),
        phone=meta.get("phone"),
        working_hours=meta.get("working_hours"),
        website=meta.get("website"),
        source_url=source_url,
        rating=meta.get("rating"),
        has_online_booking=meta.get("has_online_booking", False),
        geo=geo,
    )
    db.add(clinic)
    db.flush()
    return clinic
