"""Raw and bronze ingest layers: raw_documents and parsed_offers."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, uuid_pk
from app.models.enums import Currency, MatchStatus


class RawDocument(Base):
    """Raw layer: a fetched document stored verbatim for auditing/reparsing."""

    __tablename__ = "raw_documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    source: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    content_type: Mapped[str] = mapped_column(String(32), default="html")
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    offers: Mapped[list[ParsedOffer]] = relationship(back_populates="raw_document")


class ParsedOffer(Base):
    """Bronze layer: a row extracted as-is from a raw document."""

    __tablename__ = "parsed_offers"

    id: Mapped[uuid.UUID] = uuid_pk()
    raw_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(64), index=True)

    clinic_raw: Mapped[str | None] = mapped_column(String(512), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    service_name_raw: Mapped[str] = mapped_column(String(512), index=True)
    price_raw: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency"), default=Currency.KZT
    )
    duration_days: Mapped[int | None] = mapped_column(nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # De-duplication key: stable hash of (source, clinic, service, price).
    dedup_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    match_status: Mapped[MatchStatus] = mapped_column(
        SAEnum(MatchStatus, name="match_status"), default=MatchStatus.pending, index=True
    )
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    raw_document: Mapped[RawDocument | None] = relationship(back_populates="offers")
