"""Core data contracts and the BaseParser interface."""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field

from parsers.http import PoliteClient


@dataclass(slots=True)
class RawDoc:
    """A fetched document (raw layer)."""

    source: str
    url: str
    payload: str
    content_type: str = "html"

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.payload.encode("utf-8", "ignore")).hexdigest()


@dataclass(slots=True)
class Offer:
    """A single extracted price row (bronze layer), source-agnostic."""

    source: str
    service_name_raw: str
    price_raw: float | None
    clinic_raw: str | None = None
    city: str | None = None
    currency: str = "KZT"
    duration_days: int | None = None
    source_url: str | None = None

    def dedup_hash(self) -> str:
        key = "|".join(
            str(x).strip().lower()
            for x in (self.source, self.clinic_raw, self.city, self.service_name_raw,
                      self.price_raw, self.currency)
        )
        return hashlib.sha256(key.encode("utf-8", "ignore")).hexdigest()


@dataclass(slots=True)
class FetchResult:
    docs: list[RawDoc] = field(default_factory=list)


class BaseParser(ABC):
    """Interface every source must implement.

    Lifecycle: ``fetch()`` returns raw documents (and persists them to the raw
    layer via the pipeline), then ``parse(doc)`` turns each doc into offers.
    """

    #: Unique source slug, e.g. "kdl". Set on subclasses.
    source: str = ""
    #: Default city if the source is single-city; None if multi-city.
    default_city: str | None = None
    #: Polite crawl delay in seconds between requests to this source.
    crawl_delay: float = 1.5

    def __init__(self, client: PoliteClient | None = None,
                 offline: bool | None = None) -> None:
        from parsers.fixtures import offline_mode

        # Per-instance offline flag (defaults to the global env). Lets the
        # pipeline run a source live, then re-run it offline as a fallback.
        self.offline = offline_mode() if offline is None else offline
        self.client = client or PoliteClient(crawl_delay=self.crawl_delay)

    @abstractmethod
    def fetch(self) -> Iterable[RawDoc]:
        """Return raw documents for this source (network or fixtures)."""

    @abstractmethod
    def parse(self, doc: RawDoc) -> Iterable[Offer]:
        """Extract offers from a single raw document."""

    def run(self) -> list[Offer]:
        """Convenience: fetch all docs and parse them into offers."""
        offers: list[Offer] = []
        for doc in self.fetch():
            offers.extend(self.parse(doc))
        return offers
