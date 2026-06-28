"""Tests for text normalization and price/duration parsing helpers."""
from __future__ import annotations

from app.services.text import normalize_text
from parsers.utils import parse_duration_days, parse_price


def test_normalize_text_strips_punct_and_case():
    assert normalize_text("Общий анализ крови (ОАК)!") == "общий анализ крови оак"
    assert normalize_text("  ТТГ  ") == "ттг"
    assert normalize_text("Ёлка") == "елка"


def test_parse_price_variants():
    assert parse_price("2 500 ₸") == 2500.0
    assert parse_price("1\xa0800 тенге") == 1800.0
    assert parse_price("нет цены") is None


def test_parse_duration_days():
    assert parse_duration_days("1 к.д.") == 1
    assert parse_duration_days("срок 3 дн") == 3
    assert parse_duration_days("без срока") is None
