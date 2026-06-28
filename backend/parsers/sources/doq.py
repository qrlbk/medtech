"""Parser for doq.kz aggregator. Format: JSON API with per-clinic offers.

Unlike single-clinic sources, doq returns many clinics across cities, so the
clinic name/city come from each record rather than a class constant.
"""
from __future__ import annotations

import json
from collections.abc import Iterable

from parsers.base import BaseParser, Offer, RawDoc
from parsers.fixtures import load_fixture
from parsers.registry import register


@register
class DoqParser(BaseParser):
    source = "doq"
    default_city = None  # multi-city aggregator
    START_URLS = ["https://doq.kz/api/v1/prices"]
    FIXTURES = ["doq_aggregator.json"]

    def fetch(self) -> Iterable[RawDoc]:
        if self.offline:
            for name in self.FIXTURES:
                yield RawDoc(self.source, f"fixture://{name}", load_fixture(name),
                             content_type="json")
            return
        for url in self.START_URLS:
            yield RawDoc(self.source, url, self.client.get(url), content_type="json")

    def parse(self, doc: RawDoc) -> Iterable[Offer]:
        try:
            data = json.loads(doc.payload)
        except json.JSONDecodeError:
            return
        for rec in data.get("offers", []):
            name = (rec.get("service") or "").strip()
            if not name:
                continue
            yield Offer(
                source=self.source,
                service_name_raw=name,
                price_raw=rec.get("price"),
                clinic_raw=rec.get("clinic"),
                city=rec.get("city"),
                duration_days=rec.get("days"),
                source_url=rec.get("url", self.START_URLS[0]),
            )
