"""Service catalog: the normalized dictionary of medical services."""
from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import ServiceCategory


class ServiceCatalog(Base, TimestampMixin):
    """A canonical, normalized service (e.g. "Общий анализ крови (ОАК)")."""

    __tablename__ = "services_catalog"

    id: Mapped[uuid.UUID] = uuid_pk()
    name_norm: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[ServiceCategory] = mapped_column(
        SAEnum(ServiceCategory, name="service_category"), index=True
    )
    # Hierarchical: a service may belong to a parent group.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services_catalog.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    synonyms: Mapped[list[ServiceSynonym]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
    embedding: Mapped[ServiceEmbedding | None] = relationship(
        back_populates="service", cascade="all, delete-orphan", uselist=False
    )
    children: Mapped[list[ServiceCatalog]] = relationship()

    __table_args__ = (
        Index("ix_catalog_name_trgm", "name_norm", postgresql_using="gin",
              postgresql_ops={"name_norm": "gin_trgm_ops"}),
    )


class ServiceSynonym(Base):
    """Alias of a catalog service in some language (ru/kk/en)."""

    __tablename__ = "service_synonyms"

    id: Mapped[uuid.UUID] = uuid_pk()
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services_catalog.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(255), index=True)
    alias_norm: Mapped[str] = mapped_column(String(255), index=True)
    lang: Mapped[str] = mapped_column(String(8), default="ru")

    service: Mapped[ServiceCatalog] = relationship(back_populates="synonyms")

    __table_args__ = (
        UniqueConstraint("catalog_id", "alias_norm", name="uq_synonym_alias"),
        Index("ix_synonym_alias_trgm", "alias_norm", postgresql_using="gin",
              postgresql_ops={"alias_norm": "gin_trgm_ops"}),
    )


class ServiceEmbedding(Base):
    """Vector embedding of a catalog service for semantic matching (pgvector)."""

    __tablename__ = "service_embeddings"

    catalog_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("services_catalog.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))

    service: Mapped[ServiceCatalog] = relationship(back_populates="embedding")
