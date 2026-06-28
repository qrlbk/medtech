"""Parser for Olymp medical center (olymp.kz). Format: embedded JSON API payload."""
from __future__ import annotations

import json
import re
from collections.abc import Iterable

from parsers.base import BaseParser, Offer, RawDoc
from parsers.fixtures import load_fixture
from parsers.registry import register

_JSON_RE = re.compile(r"window\.__PRICES__\s*=\s*(\[.*?\]);", re.DOTALL)


@register
class OlympParser(BaseParser):
    source = "olymp"
    default_city = "Астана"
    START_URLS = ["https://olymp.kz/api/prices"]
    FIXTURES = ["olymp_astana.html"]
    CLINIC_NAME = "Олимп"

    def fetch(self) -> Iterable[RawDoc]:
        if self.offline:
            for name in self.FIXTURES:
                yield RawDoc(self.source, f"fixture://{name}", load_fixture(name),
                             content_type="json")
            return
        for url in self.START_URLS:
            yield RawDoc(self.source, url, self.client.get(url), content_type="json")

    def parse(self, doc: RawDoc) -> Iterable[Offer]:
        # Payload may be a raw JSON array or embedded in a <script> tag.
        text = doc.payload.strip()
        if not text.startswith("["):
            match = _JSON_RE.search(text)
            text = match.group(1) if match else "[]"
        try:
            items = json.loads(text)
        except json.JSONDecodeError:
            return
        for item in items:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            yield Offer(
                source=self.source,
                service_name_raw=name,
                price_raw=item.get("price"),
                clinic_raw=self.CLINIC_NAME,
                city=item.get("city", self.default_city),
                duration_days=item.get("days"),
                source_url=self.START_URLS[0],
            )
