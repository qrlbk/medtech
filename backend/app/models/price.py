"""Silver layer: normalized, versioned price records."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, uuid_pk


class Price(Base):
    """A normalized price for (clinic, service).

    Versioned: a new row is inserted on each change instead of overwriting,
    which yields price history for free. Only one row per (clinic, service)
    has is_active=True (the current price).
    """

    __tablename__ = "prices"

    id: Mapped[uuid.UUID] = uuid_pk()
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"), index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services_catalog.id", ondelete="CASCADE"), index=True
    )
    parsed_offer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("parsed_offers.id", ondelete="SET NULL"), nullable=True
    )

    price_kzt: Mapped[float] = mapped_column(Numeric(12, 2), index=True)
    duration_days: Mapped[int | None] = mapped_column(nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Normalization confidence in [0, 1]; low values flagged in UI.
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, index=True)

    clinic: Mapped[Clinic] = relationship(back_populates="prices")  # noqa: F821
    service: Mapped[ServiceCatalog] = relationship()  # noqa: F821

    __table_args__ = (
        Index("ix_prices_clinic_service_active", "clinic_id", "service_id", "is_active"),
    )
