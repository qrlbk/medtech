"""Tests for the KDL parser, run against a saved HTML fixture (no network)."""
from __future__ import annotations

from parsers.base import RawDoc
from parsers.fixtures import load_fixture
from parsers.sources.kdl import KdlParser


def _doc() -> RawDoc:
    return RawDoc(source="kdl", url="fixture://kdl_almaty.html",
                  payload=load_fixture("kdl_almaty.html"))


def test_parses_all_rows():
    offers = list(KdlParser().parse(_doc()))
    assert len(offers) == 10


def test_extracts_price_and_name():
    offers = {o.service_name_raw: o for o in KdlParser().parse(_doc())}
    oak = offers["Общий анализ крови (ОАК) с лейкоформулой"]
    assert oak.price_raw == 2500.0
    assert oak.currency == "KZT"
    assert oak.city == "Алматы"
    assert oak.clinic_raw == "KDL (Олимп)"


def test_extracts_duration():
    offers = {o.service_name_raw: o for o in KdlParser().parse(_doc())}
    assert offers["Витамин D (25-OH)"].duration_days == 3


def test_dedup_hash_is_stable():
    offers = list(KdlParser().parse(_doc()))
    first = offers[0]
    assert first.dedup_hash() == first.dedup_hash()
    assert len({o.dedup_hash() for o in offers}) == len(offers)
