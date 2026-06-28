"""Container entrypoint that serves the pipeline flow on a daily schedule.

Used by the `worker` service in docker-compose. Equivalent to running
`python -m pipelines.deploy`.
"""
from __future__ import annotations

from pipelines.deploy import full_pipeline_flow

if __name__ == "__main__":
    full_pipeline_flow.serve(name="medprice-daily", cron="0 3 * * *",
                             tags=["medprice", "ingest"])
