"""Parser for a Taraz clinic that publishes its price list as an Excel workbook.

Demonstrates ТЗ 3.1 Excel (XLSX) support and extends coverage to Тараз.
"""
from __future__ import annotations

from parsers.file_base import DocumentParser
from parsers.registry import register


@register
class TarazXlsxParser(DocumentParser):
    source = "taraz_med"
    default_city = "Тараз"
    crawl_delay = 2.0

    FILES = ["taraz_clinic.xlsx"]
    CLINIC_NAME = "Медцентр Аулие-Ата (Тараз)"
    SOURCE_URL = "https://auletata-taraz.kz/price.xlsx"
