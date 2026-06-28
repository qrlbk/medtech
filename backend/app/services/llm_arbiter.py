"""Optional LLM selector for borderline service-name matches.

Given a raw service name and a shortlist of catalog candidates (produced by the
fuzzy + semantic stages), asks the model to pick the best match or "none". This
is far more robust than a binary yes/no verifier when the catalog is large
(~1.3k services): the lexical/semantic stages narrow the field to a handful of
options, and the LLM makes the final, context-aware choice.

Disabled by default (``settings.llm_enabled``). Requires an OpenAI key. Any
failure degrades to ``None`` (no match) so the offer falls through to the
human-in-the-loop unmatched queue.
"""
from __future__ import annotations

import logging
import re
import uuid

from app.config import settings

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Ты — медицинский редактор-кодировщик. Тебе дают название медицинской услуги "
    "из прайса клиники и пронумерованный список кандидатов из официального "
    "справочника. Выбери номер кандидата, обозначающего ТУ ЖЕ услугу. Если ни "
    "один кандидат не подходит — ответь 0. Отвечай строго одним числом."
)
_FEWSHOT = (
    "Пример:\n"
    "Услуга: 'ОАК с лейкоформулой'\n"
    "Кандидаты:\n"
    "1. Общий анализ мочи (ОАМ)\n"
    "2. Общий анализ крови (ОАК)\n"
    "3. Биохимический анализ крови\n"
    "Ответ: 2\n"
)


def select_match(
    raw_name: str, candidates: list[tuple[uuid.UUID, str]]
) -> uuid.UUID | None:
    """Ask the LLM to pick the best catalog candidate for ``raw_name``.

    ``candidates`` is an ordered list of ``(catalog_id, catalog_name)``.
    Returns the chosen ``catalog_id`` or ``None`` (no confident match / disabled
    / error).
    """
    if not settings.llm_enabled or not settings.openai_api_key or not candidates:
        return None

    listing = "\n".join(
        f"{i}. {name}" for i, (_, name) in enumerate(candidates, start=1)
    )
    prompt = f"{_FEWSHOT}\nУслуга: '{raw_name}'\nКандидаты:\n{listing}\nОтвет:"
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=4,
        )
        answer = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001 - LLM is best-effort
        logger.warning("LLM selector failed: %s", exc)
        return None

    choice = _parse_choice(answer)
    if choice is None or not (1 <= choice <= len(candidates)):
        return None
    return candidates[choice - 1][0]


def _parse_choice(answer: str) -> int | None:
    match = re.search(r"\d+", answer)
    return int(match.group()) if match else None
