"""Human-in-the-loop queue for offers that could not be auto-normalized."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk


class UnmatchedQueue(Base):
    __tablename__ = "unmatched_queue"

    id: Mapped[uuid.UUID] = uuid_pk()
    parsed_offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parsed_offers.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Best guess from the matcher, for the reviewer to confirm/override.
    suggested_catalog_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services_catalog.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
