"""Thin Redis cache wrapper that degrades gracefully when Redis is absent."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_client = None
_failed = False


def _get_client():
    global _client, _failed
    if _client is not None or _failed:
        return _client
    try:
        import redis

        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        _client.ping()
    except Exception as exc:  # noqa: BLE001 - cache is optional
        logger.warning("Redis unavailable (%s); caching disabled.", exc)
        _failed = True
        _client = None
    return _client


def get_json(key: str) -> Any | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        return None


def set_json(key: str, value: Any, ttl: int = 300) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
    except Exception:  # noqa: BLE001
        pass


def invalidate(prefix: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        for key in client.scan_iter(f"{prefix}*"):
            client.delete(key)
    except Exception:  # noqa: BLE001
        pass
