"""Tests for binary document extraction (PDF/DOCX/XLSX/XLS) and ТЗ 3.1 sources.

All run offline against committed fixtures; no network or external services.
"""
from __future__ import annotations

import os

os.environ["MEDPRICE_OFFLINE"] = "1"

import pytest  # noqa: E402

from parsers.documents import (  # noqa: E402
    DocumentError,
    extract_docx_rows,
    extract_pdf_rows,
    extract_rows,
    extract_xls_rows,
    extract_xlsx_rows,
    format_from_filename,
)
from parsers.fixtures import FIXTURES_DIR  # noqa: E402
from parsers.sources.atyrau_docx import AtyrauDocxParser  # noqa: E402
from parsers.sources.qaragandy_pdf import QaragandyPdfParser  # noqa: E402
from parsers.sources.taraz_xlsx import TarazXlsxParser  # noqa: E402


def _bytes(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


def test_format_from_filename():
    assert format_from_filename("price.PDF") == "pdf"
    assert format_from_filename("a.docx") == "docx"
    assert format_from_filename("a.html") is None


def test_extract_pdf_keeps_cyrillic_and_prices():
    rows = extract_pdf_rows(_bytes("qaragandy_clinic.pdf"))
    flat = [c for row in rows for c in row]
    assert any("Общий анализ крови" in c for c in flat)
    assert any("2 400" in c or "2400" in c for c in flat)


def test_extract_docx_rows():
    rows = extract_docx_rows(_bytes("atyrau_clinic.docx"))
    assert rows[0][0].lower() == "услуга"
    assert any("терапевт" in c.lower() for row in rows for c in row)


def test_extract_xlsx_rows():
    rows = extract_xlsx_rows(_bytes("taraz_clinic.xlsx"))
    flat = [c for row in rows for c in row]
    assert any("УЗИ" in c for c in flat)


def test_extract_xls_rows():
    rows = extract_xls_rows(_bytes("sample_clinic.xls"))
    flat = [c.lower() for row in rows for c in row]
    assert any("терапевт" in c for c in flat)


def test_extract_rows_unsupported_format():
    with pytest.raises(DocumentError):
        extract_rows(b"x", "csv")


# -- source parsers ---------------------------------------------------------

@pytest.mark.parametrize(
    "parser_cls,city,clinic_kw,min_offers",
    [
        (QaragandyPdfParser, "Караганда", "Караганда", 8),
        (AtyrauDocxParser, "Атырау", "Атырау", 8),
        (TarazXlsxParser, "Тараз", "Тараз", 8),
    ],
    ids=lambda v: str(v),
)
def test_document_source_offers(parser_cls, city, clinic_kw, min_offers):
    offers = parser_cls().run()
    assert len(offers) >= min_offers
    assert all(o.city == city for o in offers)
    assert all(clinic_kw in (o.clinic_raw or "") for o in offers)
    # Names must be real Cyrillic text, not mojibake from a missing font.
    assert all(o.service_name_raw and "n n n" not in o.service_name_raw for o in offers)
    priced = [o for o in offers if o.price_raw and o.price_raw > 0]
    assert len(priced) == len(offers)


def test_pdf_duration_column_parsed():
    offers = {o.service_name_raw: o for o in QaragandyPdfParser().run()}
    # The PDF has a "Срок, дней" column with bare integers.
    assert offers["Витамин Д"].duration_days == 3
    assert offers["Ферритин"].duration_days == 2
