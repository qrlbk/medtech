"""Parser for an Atyrau clinic that publishes its price list as a DOCX.

Demonstrates ТЗ 3.1 DOCX support and extends market coverage to Атырау.
"""
from __future__ import annotations

from parsers.file_base import DocumentParser
from parsers.registry import register


@register
class AtyrauDocxParser(DocumentParser):
    source = "atyrau_med"
    default_city = "Атырау"
    crawl_delay = 2.0

    FILES = ["atyrau_clinic.docx"]
    CLINIC_NAME = "Клиника Жайык (Атырау)"
    SOURCE_URL = "https://zhaiyk-atyrau.kz/prays.docx"
