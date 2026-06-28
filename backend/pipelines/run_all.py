"""CLI entrypoint: run the full pipeline once (no Prefect server required).

Usage:
    python -m pipelines.run_all                # all sources
    python -m pipelines.run_all kdl invitro    # specific sources
    MEDPRICE_OFFLINE=1 python -m pipelines.run_all   # use bundled fixtures
"""
from __future__ import annotations

import json
import logging
import sys

from app.db.session import SessionLocal
from pipelines.core import run_pipeline


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    sources = argv or None
    with SessionLocal() as db:
        report = run_pipeline(db, sources)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
