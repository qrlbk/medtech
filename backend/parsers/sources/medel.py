"""Parser for MEDEL clinic (medel.kz). Format: simple 'Name — price' list."""
from __future__ import annotations

from collections.abc import Iterable

from bs4 import BeautifulSoup

from parsers.base import BaseParser, Offer, RawDoc
from parsers.fixtures import load_fixture
from parsers.registry import register
from parsers.utils import clean_text, parse_price


@register
class MedelParser(BaseParser):
    source = "medel"
    default_city = "Шымкент"
    START_URLS = ["https://medel.kz/price"]
    FIXTURES = ["medel_shymkent.html"]
    CLINIC_NAME = "МЕДЭЛ"

    def fetch(self) -> Iterable[RawDoc]:
        if self.offline:
            for name in self.FIXTURES:
                yield RawDoc(self.source, f"fixture://{name}", load_fixture(name))
            return
        for url in self.START_URLS:
            yield RawDoc(self.source, url, self.client.get(url))

    def parse(self, doc: RawDoc) -> Iterable[Offer]:
        soup = BeautifulSoup(doc.payload, "lxml")
        for li in soup.select("ul.services li"):
            text = clean_text(li.get_text())
            if "—" not in text and "-" not in text:
                continue
            sep = "—" if "—" in text else "-"
            name, _, price_part = text.rpartition(sep)
            name = clean_text(name)
            if not name:
                continue
            yield Offer(
                source=self.source,
                service_name_raw=name,
                price_raw=parse_price(price_part),
                clinic_raw=self.CLINIC_NAME,
                city=self.default_city,
                source_url=self.START_URLS[0],
            )
