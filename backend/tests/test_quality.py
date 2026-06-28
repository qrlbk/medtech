"""Tests for price validation, currency conversion, anomaly detection."""
from __future__ import annotations

from app.services.quality import USD_TO_KZT, is_anomalous, to_kzt, validate_price


def test_usd_converted_to_kzt():
    assert to_kzt(100, "USD") == round(100 * USD_TO_KZT, 2)
    assert to_kzt(2500, "KZT") == 2500.0


def test_rejects_non_positive_and_out_of_range():
    assert validate_price(0, "KZT").ok is False
    assert validate_price(-5, "KZT").ok is False
    assert validate_price(10, "KZT").reason == "below_min"
    assert validate_price(9_000_000, "KZT").reason == "above_max"


def test_accepts_plausible_price():
    check = validate_price(2500, "KZT")
    assert check.ok is True
    assert check.price_kzt == 2500.0


def test_anomaly_detection():
    assert is_anomalous(50000, 2500) is True   # 20x jump
    assert is_anomalous(2600, 2500) is False
    assert is_anomalous(2500, None) is False
