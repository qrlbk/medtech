"""Helpers to load bundled HTML fixtures for offline parsing and tests."""
from __future__ import annotations

import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures"


def offline_mode() -> bool:
    """When true, parsers read bundled fixtures instead of the network.

    Useful for deterministic tests, CI, and seeding demo data without
    hitting live sources.
    """
    return os.getenv("MEDPRICE_OFFLINE", "0") in {"1", "true", "True"}


def load_fixture(name: str) -> str:
    path = FIXTURES_DIR / name
    return path.read_text(encoding="utf-8")
