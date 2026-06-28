"""Prefect flow/task wrappers around the plain pipeline functions.

Per-source ingestion runs as isolated tasks so a single failing source is
retried and contained without aborting the whole flow.
"""
from __future__ import annotations

from prefect import flow, get_run_logger, task

from app.db.session import SessionLocal
from parsers.registry import known_sources
from pipelines.core import ingest_source, run_pipeline


@task(retries=2, retry_delay_seconds=30, task_run_name="ingest-{source}")
def ingest_source_task(source: str) -> dict:
    with SessionLocal() as db:
        run = ingest_source(db, source)
        return {"source": source, "status": run.status, "new": run.offers_new}


@flow(name="ingest-all")
def ingest_flow(sources: list[str] | None = None) -> list[dict]:
    logger = get_run_logger()
    sources = sources or known_sources()
    # Submit per-source tasks concurrently; failures are isolated per task.
    futures = [ingest_source_task.submit(s) for s in sources]
    results = [f.result(raise_on_failure=False) for f in futures]
    logger.info("Ingest finished: %s", results)
    return results


@flow(name="full-pipeline")
def full_pipeline_flow(sources: list[str] | None = None) -> dict:
    with SessionLocal() as db:
        return run_pipeline(db, sources)
