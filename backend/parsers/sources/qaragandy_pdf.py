"""Parser for a Karaganda clinic that publishes its price list as a PDF.

Demonstrates ТЗ 3.1 PDF support and extends market coverage to Караганда.
"""
from __future__ import annotations

from parsers.file_base import DocumentParser
from parsers.registry import register


@register
class QaragandyPdfParser(DocumentParser):
    source = "qaragandy_med"
    default_city = "Караганда"
    crawl_delay = 2.0

    FILES = ["qaragandy_clinic.pdf"]
    CLINIC_NAME = "Медцентр Сункар (Караганда)"
    SOURCE_URL = "https://sunqar-karaganda.kz/price.pdf"
