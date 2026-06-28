"""Admin (human-in-the-loop) schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class UnmatchedItem(BaseModel):
    id: uuid.UUID
    parsed_offer_id: uuid.UUID
    service_name_raw: str
    source: str
    clinic_raw: str | None = None
    city: str | None = None
    price_raw: float | None = None
    suggested_catalog_id: uuid.UUID | None = None
    suggested_name: str | None = None
    score: float | None = None


class ResolveIn(BaseModel):
    catalog_id: uuid.UUID | None = None  # None => reject as not-a-service
    add_as_synonym: bool = True


class IngestTriggerOut(BaseModel):
    status: str
    detail: str
