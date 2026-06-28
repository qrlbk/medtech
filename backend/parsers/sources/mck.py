"""Parser for MCK medical center (mck.kz, Aktobe). Format: tariffs table."""
from __future__ import annotations

from collections.abc import Iterable

from bs4 import BeautifulSoup

from parsers.base import BaseParser, Offer, RawDoc
from parsers.fixtures import load_fixture
from parsers.registry import register
from parsers.utils import clean_text, parse_price


@register
class MckParser(BaseParser):
    source = "mck"
    default_city = "Актобе"
    START_URLS = ["https://mck.kz/tariffs"]
    FIXTURES = ["mck_aktobe.html"]
    CLINIC_NAME = "Медицинский центр МЦК"

    def fetch(self) -> Iterable[RawDoc]:
        if self.offline:
            for name in self.FIXTURES:
                yield RawDoc(self.source, f"fixture://{name}", load_fixture(name))
            return
        for url in self.START_URLS:
            yield RawDoc(self.source, url, self.client.get(url))

    def parse(self, doc: RawDoc) -> Iterable[Offer]:
        soup = BeautifulSoup(doc.payload, "lxml")
        for row in soup.select("table.tariffs tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            name = clean_text(cells[0].get_text())
            if not name:
                continue
            yield Offer(
                source=self.source,
                service_name_raw=name,
                price_raw=parse_price(cells[-1].get_text()),
                clinic_raw=self.CLINIC_NAME,
                city=self.default_city,
                source_url=self.START_URLS[0],
            )
