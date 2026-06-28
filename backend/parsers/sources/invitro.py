"""Parser for INVITRO (invitro.kz).

The live catalog at ``/analizes/`` server-renders every test as a
``div.item_card`` with the name in ``.analyzes-item__title a`` and the price in
``.analyzes-item__total--sum``. Names carry an English translation in trailing
parentheses which we strip before normalization. The bundled fixture uses a
simpler ``div.price-item`` layout (with delivery terms), still parsed here for
offline / fallback runs.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from bs4 import BeautifulSoup

from parsers.base import BaseParser, Offer, RawDoc
from parsers.fixtures import load_fixture
from parsers.registry import register
from parsers.utils import clean_text, parse_duration_days, parse_price

# Trailing "(English translation ...)" appended to RU names on invitro.kz.
_EN_PARENS_RE = re.compile(r"\s*\([^()]*[A-Za-z][^()]*\)\s*$")
# Trailing ", English name" with no Cyrillic after the last comma.
_EN_COMMA_RE = re.compile(r",\s*[A-Za-z][^,А-Яа-яЁё]*$")


def _clean_name(raw: str) -> str:
    name = clean_text(raw)
    prev = None
    while name != prev:  # peel possibly-stacked trailing latin tails
        prev = name
        name = _EN_PARENS_RE.sub("", name).strip()
        name = _EN_COMMA_RE.sub("", name).strip()
    return name


@register
class InvitroParser(BaseParser):
    source = "invitro"
    default_city = "Алматы"
    crawl_delay = 2.0
    START_URLS = ["https://www.invitro.kz/analizes/"]
    FIXTURES = ["invitro_almaty.html"]
    CLINIC_NAME = "Инвитро"
    BASE = "https://www.invitro.kz"
    # The live page lists 2000+ tests; cap to keep ingest/normalization sane.
    MAX_ITEMS = 300

    def fetch(self) -> Iterable[RawDoc]:
        if self.offline:
            for name in self.FIXTURES:
                yield RawDoc(self.source, f"fixture://{name}", load_fixture(name))
            return
        for url in self.START_URLS:
            yield RawDoc(self.source, url, self.client.get(url))

    def parse(self, doc: RawDoc) -> Iterable[Offer]:
        soup = BeautifulSoup(doc.payload, "lxml")
        cards = soup.select("div.item_card")
        if cards:
            yield from self._parse_live(cards)
            return
        # Fixture layout: div.price-item with .name/.cost/.term.
        for item in soup.select("div.price-item"):
            name_el = item.select_one(".name")
            name = clean_text(name_el.get_text() if name_el else "")
            if not name:
                continue
            cost = item.select_one(".cost")
            term = item.select_one(".term")
            yield Offer(
                source=self.source,
                service_name_raw=name,
                price_raw=parse_price(cost.get_text() if cost else None),
                clinic_raw=self.CLINIC_NAME,
                city=self.default_city,
                duration_days=parse_duration_days(term.get_text() if term else None),
                source_url=self.START_URLS[0],
            )

    def _parse_live(self, cards) -> Iterable[Offer]:
        seen = 0
        for card in cards:
            a = card.select_one(".analyzes-item__title a")
            if not a:
                continue
            name = _clean_name(a.get_text(" ", strip=True))
            sum_el = card.select_one(".analyzes-item__total--sum")
            price = parse_price(sum_el.get_text()) if sum_el else None
            if not name or price is None:
                continue
            href = a.get("href", "")
            yield Offer(
                source=self.source,
                service_name_raw=name,
                price_raw=price,
                clinic_raw=self.CLINIC_NAME,
                city=self.default_city,
                source_url=f"{self.BASE}{href}" if href.startswith("/") else self.BASE,
            )
            seen += 1
            if seen >= self.MAX_ITEMS:
                break
