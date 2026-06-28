"""Tests for the official catalog importer (category inference + file shape)."""
from __future__ import annotations

import pytest

from app.models.enums import ServiceCategory
from app.scripts.import_catalog import DATA_FILE, infer_category


@pytest.mark.parametrize(
    "name,specialty,expected",
    [
        ("Прием акушер-гинеколога", "Акушер-гинеколог", ServiceCategory.doctor_visit),
        ("Консультация кардиолога", "Кардиолог", ServiceCategory.doctor_visit),
        ("3D УЗИ плода", "Акушер-гинеколог", ServiceCategory.diagnostics),
        ("ФГДС", "Гастроэнтеролог", ServiceCategory.diagnostics),
        ("МРТ головного мозга", "Невролог", ServiceCategory.diagnostics),
        ("Общий анализ крови", "Лаборатория", ServiceCategory.laboratory),
        ("Забор гинекологического мазка", "Гинеколог", ServiceCategory.laboratory),
        ("Массаж простаты", "Андролог", ServiceCategory.procedure),
    ],
)
def test_infer_category(name, specialty, expected):
    assert infer_category(name, specialty) == expected


@pytest.mark.skipif(not DATA_FILE.exists(), reason="official catalog file absent")
def test_official_catalog_is_readable_and_large():
    from parsers.documents import extract_xlsx_rows

    rows = extract_xlsx_rows(DATA_FILE.read_bytes())
    header = [c.lower() for c in rows[0]]
    assert "name_ru" in header and "специальность" in header
    # The organizer reference holds well over a thousand services.
    assert len(rows) > 1000
