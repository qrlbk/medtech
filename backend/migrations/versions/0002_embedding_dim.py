"""Resize service embedding vectors to the configured dimension.

Lets the embedding provider change (e.g. local 384-dim MiniLM -> OpenAI
1536-dim ``text-embedding-3-small``). A dimension change invalidates stored
vectors, so existing rows are cleared and recomputed later by
``backfill_embeddings``. The target dimension is read from settings, so set
``EMBEDDING_DIM`` (and ``EMBEDDING_PROVIDER``) before running this migration.

Revision ID: 0002_embedding_dim
Revises: 0001_initial
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

from app.config import settings

revision = "0002_embedding_dim"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dim = int(settings.embedding_dim)
    # Clear vectors first: a dimension change makes the old ones unusable.
    op.execute("DELETE FROM service_embeddings")
    op.execute(
        f"ALTER TABLE service_embeddings ALTER COLUMN embedding TYPE vector({dim})"
    )


def downgrade() -> None:
    op.execute("DELETE FROM service_embeddings")
    op.execute("ALTER TABLE service_embeddings ALTER COLUMN embedding TYPE vector(384)")
