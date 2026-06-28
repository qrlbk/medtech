"""Parser for KDL laboratory (kdl.kz / kdlolymp.kz) price lists.

KDL publishes analyses as a price table. This parser handles the common
"price-list table" layout: rows of (service name, turnaround, price).
"""
from __future__ import annotations

from collections.abc import Iterable

from bs4 import BeautifulSoup

from parsers.base import BaseParser, Offer, RawDoc
from parsers.fixtures import load_fixture
from parsers.registry import register
from parsers.utils import clean_text, parse_duration_days, parse_price


@register
class KdlParser(BaseParser):
    source = "kdl"
    default_city = "Алматы"
    crawl_delay = 2.0

    START_URLS = [
        "https://kdl.kz/analizy-i-tseny",
    ]
    FIXTURES = ["kdl_almaty.html"]
    CLINIC_NAME = "KDL (Олимп)"

    def fetch(self) -> Iterable[RawDoc]:
        if self.offline:
            for name in self.FIXTURES:
                yield RawDoc(source=self.source, url=f"fixture://{name}",
                             payload=load_fixture(name))
            return
        for url in self.START_URLS:
            yield RawDoc(source=self.source, url=url, payload=self.client.get(url))

    def parse(self, doc: RawDoc) -> Iterable[Offer]:
        soup = BeautifulSoup(doc.payload, "lxml")
        for row in soup.select("table.price-list tbody tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            name = clean_text(cells[0].get_text())
            if not name:
                continue
            # Price is the last numeric cell; duration may be in a middle cell.
            price = parse_price(cells[-1].get_text())
            duration = None
            if len(cells) >= 3:
                duration = parse_duration_days(cells[1].get_text())
            yield Offer(
                source=self.source,
                service_name_raw=name,
                price_raw=price,
                clinic_raw=self.CLINIC_NAME,
                city=self.default_city,
                currency="KZT",
                duration_days=duration,
                source_url=doc.url if doc.url.startswith("http") else self.START_URLS[0],
            )
