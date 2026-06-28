"""Base class for parsers that read binary price-list documents (PDF/DOCX/XLS).

A :class:`DocumentParser` fetches files (bundled fixtures in offline mode, or a
configured directory in live mode), stores their bytes base64-encoded in the
raw layer, then extracts tabular rows and maps them to :class:`Offer` records.

Subclasses usually only declare a few class attributes (clinic, city, file
list). Column detection is heuristic by default but can be pinned per source.
"""
from __future__ import annotations

import base64
import logging
import os
from collections.abc import Iterable
from pathlib import Path

from parsers.base import BaseParser, Offer, RawDoc
from parsers.documents import extract_rows, format_from_filename
from parsers.fixtures import FIXTURES_DIR
from parsers.utils import clean_text, parse_duration_days, parse_price

logger = logging.getLogger(__name__)

#: Header keywords used to auto-detect columns in a heterogeneous price list.
_PRICE_HEADERS = ("цена", "стоимость", "тенге", "тг", "price", "kzt", "сумма")
_NAME_HEADERS = (
    "услуг", "наименование", "название", "анализ", "исследован",
    "name", "сервис", "процедур", "прием", "приём",
)
_DURATION_HEADERS = ("срок", "дней", "готовност", "day", "выполнен")


def _looks_numeric(value: str) -> bool:
    return parse_price(value) is not None


def _parse_days(value: str) -> int | None:
    """Turnaround in days. Accepts '1 к.д.' and bare counts from a 'дней' column."""
    days = parse_duration_days(value)
    if days is not None:
        return days
    stripped = value.strip()
    if stripped.isdigit():
        return int(stripped)
    return None


class DocumentParser(BaseParser):
    """Parse price lists from PDF/DOCX/XLSX/XLS documents."""

    #: Fixture filenames (relative to the fixtures dir) used in offline mode.
    FILES: list[str] = []
    #: Clinic these files belong to (single-clinic document sources).
    CLINIC_NAME: str = "Неизвестная клиника"
    #: Public URL the document was published at (for source attribution).
    SOURCE_URL: str | None = None

    #: Optional pinned column indices; when None, columns are auto-detected.
    NAME_COL: int | None = None
    PRICE_COL: int | None = None
    DURATION_COL: int | None = None
    #: Number of leading rows to always skip (titles/legends above the header).
    SKIP_ROWS: int = 0

    def _files_dir(self) -> Path:
        """Directory to read live files from (override via MEDPRICE_FILES_DIR)."""
        return Path(os.getenv("MEDPRICE_FILES_DIR", str(FIXTURES_DIR)))

    def fetch(self) -> Iterable[RawDoc]:
        directory = FIXTURES_DIR if self.offline else self._files_dir()
        for name in self.FILES:
            fmt = format_from_filename(name)
            if fmt is None:
                logger.warning("%s: unsupported document %s, skipping", self.source, name)
                continue
            path = directory / name
            if not path.exists():
                logger.warning("%s: file not found: %s", self.source, path)
                continue
            payload = base64.b64encode(path.read_bytes()).decode("ascii")
            yield RawDoc(
                source=self.source,
                url=self.SOURCE_URL or f"file://{name}",
                payload=payload,
                content_type=fmt,
            )

    def parse(self, doc: RawDoc) -> Iterable[Offer]:
        try:
            data = base64.b64decode(doc.payload)
            rows = extract_rows(data, doc.content_type)
        except Exception as exc:  # noqa: BLE001 - one bad doc shouldn't kill source
            logger.warning("%s: failed to extract %s: %s", self.source, doc.url, exc)
            return
        yield from self.rows_to_offers(rows, doc)

    # -- row mapping -------------------------------------------------------

    def rows_to_offers(self, rows: list[list[str]], doc: RawDoc) -> Iterable[Offer]:
        yield from offers_from_rows(
            rows,
            source=self.source,
            clinic=self.CLINIC_NAME,
            city=self.default_city,
            source_url=self.SOURCE_URL or doc.url,
            skip_rows=self.SKIP_ROWS,
            name_col=self.NAME_COL,
            price_col=self.PRICE_COL,
            duration_col=self.DURATION_COL,
        )


def offers_from_rows(
    rows: list[list[str]],
    *,
    source: str,
    clinic: str | None,
    city: str | None,
    source_url: str | None,
    skip_rows: int = 0,
    name_col: int | None = None,
    price_col: int | None = None,
    duration_col: int | None = None,
) -> Iterable[Offer]:
    """Map extracted document rows to :class:`Offer` records.

    Shared by document source parsers and the admin file-upload endpoint, so a
    user-uploaded price list is parsed with exactly the same column heuristics.
    """
    rows = rows[skip_rows:]
    if not rows:
        return
    header_idx, (nc, pc, dc) = resolve_columns(rows, name_col, price_col, duration_col)
    if nc is None or pc is None:
        logger.warning("%s: could not locate name/price columns", source)
        return

    for row in rows[header_idx + 1:]:
        if max(nc, pc) >= len(row):
            continue
        name = clean_text(row[nc])
        price = parse_price(row[pc])
        if not name or price is None:
            continue
        duration = None
        if dc is not None and dc < len(row):
            duration = _parse_days(row[dc])
        yield Offer(
            source=source,
            service_name_raw=name,
            price_raw=price,
            clinic_raw=clinic,
            city=city,
            currency="KZT",
            duration_days=duration,
            source_url=source_url,
        )


def resolve_columns(
    rows: list[list[str]],
    name_col: int | None = None,
    price_col: int | None = None,
    duration_col: int | None = None,
) -> tuple[int, tuple[int | None, int | None, int | None]]:
    """Return (header_row_index, (name_col, price_col, duration_col))."""
    if name_col is not None and price_col is not None:
        # Columns pinned by the caller: treat row 0 as the header.
        return 0, (name_col, price_col, duration_col)

    header_idx, header = _find_header(rows)
    if header is not None:
        name_col = name_col if name_col is not None else _match_header(header, _NAME_HEADERS)
        price_col = price_col if price_col is not None else _match_header(header, _PRICE_HEADERS)
        duration_col = (
            duration_col if duration_col is not None
            else _match_header(header, _DURATION_HEADERS)
        )

    data_rows = rows[header_idx + 1:] if header is not None else rows
    if price_col is None:
        price_col = _infer_price_col(data_rows)
    if name_col is None or name_col == price_col:
        name_col = _infer_name_col(data_rows, exclude=price_col)
    return header_idx, (name_col, price_col, duration_col)


def _find_header(rows: list[list[str]]) -> tuple[int, list[str] | None]:
    """Locate a header row by matching name/price keywords; default row 0."""
    for idx, row in enumerate(rows[:10]):
        joined = " ".join(row).lower()
        if any(k in joined for k in _PRICE_HEADERS) and any(
            k in joined for k in _NAME_HEADERS
        ):
            return idx, row
    return -1, None


def _match_header(header: list[str], keywords: tuple[str, ...]) -> int | None:
    for i, cell in enumerate(header):
        low = cell.lower()
        if any(k in low for k in keywords):
            return i
    return None


def _infer_price_col(rows: list[list[str]]) -> int | None:
    """Pick the column that most often holds a parseable price (prefer rightmost)."""
    width = max((len(r) for r in rows), default=0)
    best_col, best_score = None, 0
    for col in range(width):
        score = sum(
            1 for r in rows if col < len(r) and _looks_numeric(r[col])
        )
        # >= keeps the rightmost column on ties (prices are usually last).
        if score >= best_score and score > 0:
            best_col, best_score = col, score
    return best_col


def _infer_name_col(rows: list[list[str]], exclude: int | None) -> int | None:
    """Pick the text-heaviest column (longest average non-numeric content)."""
    width = max((len(r) for r in rows), default=0)
    best_col, best_len = None, 0.0
    for col in range(width):
        if col == exclude:
            continue
        texts = [r[col] for r in rows if col < len(r) and not _looks_numeric(r[col])]
        if not texts:
            continue
        avg = sum(len(t) for t in texts) / len(texts)
        if avg > best_len:
            best_col, best_len = col, avg
    return best_col
