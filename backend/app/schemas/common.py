"""Shared Pydantic schemas for API responses."""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.models.enums import ServiceCategory


class ServiceSuggestion(BaseModel):
    id: uuid.UUID
    name: str
    category: ServiceCategory


class ServiceOut(BaseModel):
    id: uuid.UUID
    name: str
    category: ServiceCategory


class ClinicBrief(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    address: str | None = None
    phone: str | None = None
    working_hours: str | None = None
    website: str | None = None
    rating: float | None = None
    has_online_booking: bool = False
    lat: float | None = None
    lon: float | None = None


class PriceOffer(BaseModel):
    price_id: uuid.UUID
    price_kzt: float
    duration_days: int | None = None
    parsed_at: str | None = None
    is_fresh: bool = False
    confidence: float = 1.0
    source_url: str | None = None
    clinic: ClinicBrief
    distance_m: float | None = None


class SearchResponse(BaseModel):
    service: ServiceOut
    count: int
    results: list[PriceOffer]
    analytics: dict


class Analytics(BaseModel):
    min_price: float | None = None
    avg_price: float | None = None
    max_price: float | None = None
    clinic_count: int = 0


class StatsOut(BaseModel):
    services: int
    synonyms: int
    clinics: int
    cities: int
    active_prices: int
    sources: int
    unmatched: int
