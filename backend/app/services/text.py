"""Text normalization shared by catalog seeding and the matcher."""
from __future__ import annotations

import re

_PUNCT_RE = re.compile(r"[^\w\s\-]", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_text(value: str | None) -> str:
    """Lowercase, strip punctuation/extra spaces; language-agnostic.

    Used to build a comparable key for exact/synonym matching, e.g.
    "Общий анализ крови (ОАК)!" -> "общий анализ крови оак".
    """
    if not value:
        return ""
    text = value.lower().replace("ё", "е")
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()
