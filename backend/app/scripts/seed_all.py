"""One-shot seeding: catalog + admin user + offline ingest/normalize/index.

Run after `alembic upgrade head`. Uses bundled fixtures (MEDPRICE_OFFLINE=1)
so it populates realistic demo data without hitting live sources.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import func, select

from app.config import settings
from app.db.session import SessionLocal
from app.models import Clinic, Price, ServiceCatalog, User
from app.scripts.import_catalog import import_official_catalog
from app.scripts.seed_catalog import backfill_embeddings, seed_catalog
from app.security import hash_password

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "admin@medprice.kz"
ADMIN_PASSWORD = "admin"


def ensure_admin(db) -> None:
    if db.scalar(select(User).where(User.email == ADMIN_EMAIL)):
        return
    db.add(User(email=ADMIN_EMAIL, hashed_password=hash_password(ADMIN_PASSWORD),
                is_admin=True))
    db.commit()
    logger.info("Created admin user %s (password: %s)", ADMIN_EMAIL, ADMIN_PASSWORD)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    # Force offline mode so seeding uses bundled fixtures.
    os.environ.setdefault("MEDPRICE_OFFLINE", "1")

    with SessionLocal() as db:
        seed_catalog(db)
        # Import the official organizer-provided reference (~1.3k services), if present.
        import_official_catalog(db)
        # Embed services added by the official import (seed_catalog ran before it),
        # so semantic matching covers the full catalog, not just the JSON seed.
        backfill_embeddings(db)
        db.commit()
        ensure_admin(db)

    # Import after env is set so parsers pick up offline mode.
    from pipelines.core import run_pipeline

    with SessionLocal() as db:
        report = run_pipeline(db)
        services = db.scalar(select(func.count(ServiceCatalog.id)))
        clinics = db.scalar(select(func.count(Clinic.id)))
        prices = db.scalar(select(func.count(Price.id)).where(Price.is_active.is_(True)))

    logger.info("Seed complete. services=%s clinics=%s active_prices=%s",
                services, clinics, prices)
    logger.info("Pipeline report: %s", report)
    print(f"DATA_FRESH_DAYS={settings.data_fresh_days}")


if __name__ == "__main__":
    main()
