"""Register a daily Prefect schedule for the full pipeline (ТЗ: >=1/day)."""
from __future__ import annotations

from pipelines.flows import full_pipeline_flow

if __name__ == "__main__":
    # Serve the flow with a daily cron schedule (03:00 Asia/Almaty).
    full_pipeline_flow.serve(
        name="medprice-daily",
        cron="0 3 * * *",
        tags=["medprice", "ingest"],
    )
