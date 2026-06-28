"""Text/price parsing helpers shared by source parsers."""
from __future__ import annotations

import re

_PRICE_RE = re.compile(r"(\d[\d\s.,]*\d|\d)")
_DURATION_RE = re.compile(r"(\d+)\s*(?:к\.?д|кд|раб(?:очих)?\.?\s*дн|дн|сут|day)", re.IGNORECASE)


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_price(text: str | None) -> float | None:
    """Extract a numeric price from messy text like '1 200 ₸' or '2.500,00'."""
    if not text:
        return None
    match = _PRICE_RE.search(text.replace("\xa0", " "))
    if not match:
        return None
    raw = match.group(1).strip()
    # Remove thousands separators (spaces); handle comma decimals.
    raw = raw.replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def parse_duration_days(text: str | None) -> int | None:
    """Extract turnaround time in days from text like 'срок 1 к.д.'."""
    if not text:
        return None
    match = _DURATION_RE.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None
