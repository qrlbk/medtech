"""Smoke tests for all registered sources, run offline against fixtures."""
from __future__ import annotations

import os

os.environ["MEDPRICE_OFFLINE"] = "1"

import pytest  # noqa: E402

from parsers.registry import iter_parsers, known_sources  # noqa: E402

EXPECTED = {
    "kdl", "invitro", "helix", "olymp", "medel", "mck", "doq",
    # Document-based sources (PDF / DOCX / XLSX) — ТЗ 3.1 format support.
    "qaragandy_med", "atyrau_med", "taraz_med",
}


def test_all_sources_registered():
    assert EXPECTED.issubset(set(known_sources()))
    assert len(known_sources()) >= 9  # 7 HTML/JSON + 3 document sources


@pytest.mark.parametrize("parser", list(iter_parsers()), ids=lambda p: p.source)
def test_source_yields_priced_offers(parser):
    offers = parser.run()
    assert len(offers) > 0, f"{parser.source} produced no offers"
    priced = [o for o in offers if o.price_raw and o.price_raw > 0]
    assert len(priced) >= max(1, int(len(offers) * 0.8))
    # Every offer carries the source slug and a service name.
    assert all(o.source == parser.source and o.service_name_raw for o in offers)
