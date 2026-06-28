"""Parser for Helix (helix.kz).

Helix runs a server-side-rendered Angular catalog: each category page at
``/catalog/<id>-<slug>`` lists service cards (``a.card[href^="/catalog/item/"]``)
with the name in a ``.typography-headline`` element and the price as ``N ₸``.
Card names carry a code prefix ("Анализ 02-029 …", "Услуга 90-040 …") which we
strip before normalization.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from bs4 import BeautifulSoup

from parsers.base import BaseParser, Offer, RawDoc
from parsers.fixtures import load_fixture
from parsers.registry import register
from parsers.utils import clean_text, parse_price

# Strip the leading kind + code, e.g. "Анализ 02-029 ", "Услуга 90-040 ".
_PREFIX_RE = re.compile(
    r"^(?:Комплекс|Анализ|Услуга|Профиль|Исследование)\s+\S+\s+", re.IGNORECASE
)
_PRICE_RE = re.compile(r"(\d[\d\s\u00a0]*)\s*₸")


@register
class HelixParser(BaseParser):
    source = "helix"
    default_city = "Алматы"
    crawl_delay = 1.0

    BASE = "https://helix.kz"
    # A spread of categories across the ТЗ taxonomy (labs, hormones, diagnostics,
    # doctor visits). Helix server-renders the first page of each category.
    CATEGORIES = [
        "/catalog/3-obschij-analiz-krovi",
        "/catalog/28-biohimicheskie-analizy",
        "/catalog/29-analizy-na-gormony",
        "/catalog/189-analizy-na-vitaminy",
        "/catalog/23-analizy-na-infekcii",
        "/catalog/178-uzi-ultrazvukovye-issledovaniya",
        "/catalog/179-ekg-elektrokardiogramma",
        "/catalog/191-vrachebnye-uslugi",
    ]
    FIXTURES = ["helix_almaty.html"]
    CLINIC_NAME = "Хеликс"

    def fetch(self) -> Iterable[RawDoc]:
        if self.offline:
            for name in self.FIXTURES:
                yield RawDoc(self.source, f"fixture://{name}", load_fixture(name))
            return
        for path in self.CATEGORIES:
            url = self.BASE + path
            try:
                yield RawDoc(self.source, url, self.client.get(url))
            except Exception:  # noqa: BLE001 - skip a bad category, keep the rest
                continue

    def parse(self, doc: RawDoc) -> Iterable[Offer]:
        soup = BeautifulSoup(doc.payload, "lxml")
        for card in soup.select('a.card[href^="/catalog/item/"]'):
            name_el = card.select_one(".typography-headline")
            raw = name_el.get("title") if name_el and name_el.get("title") else (
                name_el.get_text(" ", strip=True) if name_el else ""
            )
            name = _PREFIX_RE.sub("", clean_text(raw)).strip()
            if not name:
                continue
            m = _PRICE_RE.search(card.get_text(" ", strip=True))
            price = parse_price(m.group(1)) if m else None
            if price is None:
                continue
            href = card.get("href", "")
            yield Offer(
                source=self.source,
                service_name_raw=name,
                price_raw=price,
                clinic_raw=self.CLINIC_NAME,
                city=self.default_city,
                currency="KZT",
                source_url=f"{self.BASE}{href}" if href.startswith("/") else doc.url,
            )
