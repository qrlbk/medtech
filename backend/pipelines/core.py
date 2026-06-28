"""Plain (Prefect-free) pipeline functions.

Kept dependency-light so they run via a simple CLI (`run_all`) or be wrapped
by Prefect flows. Each source is isolated: one failing source never stops the
others (ТЗ fault-tolerance requirement).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import ParseRun
from app.services.ingest import persist_offers, persist_raw_doc
from app.services.normalization import NormalizeStats, normalize_pending
from parsers.fixtures import offline_mode
from parsers.registry import get_parser, known_sources

logger = logging.getLogger(__name__)


def _ingest_with_parser(db: Session, parser) -> tuple[int, int]:
    """Fetch + parse + persist for one parser instance. Returns (found, new)."""
    found = new = 0
    for doc in parser.fetch():
        raw = persist_raw_doc(db, doc)
        offers = list(parser.parse(doc))
        found += len(offers)
        new += persist_offers(db, offers, raw)
    return found, new


def ingest_source(db: Session, source: str) -> ParseRun:
    """Fetch + parse + persist a single source. Records a ParseRun journal row.

    In live mode, if a source yields nothing (site blocked/changed), we fall
    back to its bundled fixture so the demo still has data — recorded in the
    run's error note as ``fixture_fallback``.
    """
    run = ParseRun(source=source, status="running")
    db.add(run)
    db.flush()
    found = new = 0
    try:
        parser = get_parser(source)
        found, new = _ingest_with_parser(db, parser)
        note = None
        if found == 0 and not offline_mode():
            # Live attempt produced nothing: retry from the bundled fixture.
            fallback = get_parser(source, offline=True)
            found, new = _ingest_with_parser(db, fallback)
            if found:
                note = "fixture_fallback"
                logger.info("Source %s: live empty, used fixture fallback", source)
        run.status = "success"
        run.offers_found = found
        run.offers_new = new
        run.error = note
    except Exception as exc:  # noqa: BLE001 - isolate per-source failures
        db.rollback()
        run = db.merge(run)
        # Live fetch crashed (site blocked/unreachable): try the fixture so the
        # pipeline still yields data for this source.
        if not offline_mode():
            try:
                f, n = _ingest_with_parser(db, get_parser(source, offline=True))
                if f:
                    run.status = "success"
                    run.offers_found, run.offers_new = f, n
                    run.error = "fixture_fallback (live error)"
                    logger.info("Source %s: live error, used fixture fallback", source)
                    db.flush()
                else:
                    raise exc
            except Exception:  # noqa: BLE001
                db.rollback()
                run = db.merge(run)
                run.status = "error"
                run.error = str(exc)
                logger.warning("Source %s failed (no fixture): %s", source, exc)
        else:
            run.status = "error"
            run.error = str(exc)
            logger.exception("Source %s failed: %s", source, exc)
    finally:
        run.finished_at = datetime.now(UTC)
        db.commit()
    try:
        from app.observability.metrics import PARSER_SUCCESS

        PARSER_SUCCESS.labels(source, run.status).inc()
    except Exception:  # noqa: BLE001 - metrics optional
        pass
    return run


def ingest_all(db: Session, sources: list[str] | None = None) -> list[ParseRun]:
    sources = sources or known_sources()
    runs = []
    for source in sources:
        runs.append(ingest_source(db, source))
    return runs


def run_pipeline(db: Session, sources: list[str] | None = None) -> dict:
    """Full pipeline: ingest -> normalize -> reindex search -> cleanup raw."""
    runs = ingest_all(db, sources)
    stats: NormalizeStats = normalize_pending(db)

    indexed = 0
    try:
        from app.services.search import reindex_all

        indexed = reindex_all(db)
    except Exception as exc:  # noqa: BLE001 - search is optional at pipeline time
        logger.warning("Reindex skipped: %s", exc)

    cleaned = 0
    try:
        from app.services.quality import cleanup_old_raw

        cleaned = cleanup_old_raw(db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Raw cleanup skipped: %s", exc)

    notified = 0
    try:
        from app.services.notifications import check_subscriptions

        notified = check_subscriptions(db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Subscription check skipped: %s", exc)

    return {
        "sources": {r.source: {"status": r.status, "new": r.offers_new} for r in runs},
        "normalize": stats.__dict__,
        "indexed": indexed,
        "raw_cleaned": cleaned,
        "notified": notified,
    }
