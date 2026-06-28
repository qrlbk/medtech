"""Minimal Telegram Bot API client + long-polling bot.

The bot lets users search for the cheapest price for a service from chat.
Both sending and polling degrade gracefully when no token is configured.
"""
from __future__ import annotations

import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
API = "https://api.telegram.org/bot{token}/{method}"


def is_configured() -> bool:
    return bool(settings.telegram_bot_token)


def send_message(chat_id: str, text: str) -> bool:
    if not is_configured():
        logger.info("[telegram disabled] -> %s: %s", chat_id, text)
        return False
    try:
        resp = httpx.post(
            API.format(token=settings.telegram_bot_token, method="sendMessage"),
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram send failed: %s", exc)
        return False


def _handle_query(db, text: str) -> str:
    from app.services import search as search_svc
    from app.services.serving import PriceFilters, search_prices

    suggestions = search_svc.autocomplete(db, text, limit=1)
    if not suggestions:
        return "Не нашёл такую услугу. Попробуйте иначе, например «ОАК» или «УЗИ почек»."
    s = suggestions[0]
    offers = search_prices(db, s["id"], PriceFilters(), sort="price_asc", limit=5)
    if not offers:
        return f"По услуге «{s['name']}» пока нет цен в базе."
    lines = [f"<b>{s['name']}</b> — дешевле всего:"]
    for o in offers:
        lines.append(
            f"• {int(o['price_kzt'])} ₸ — {o['clinic']['name']} ({o['clinic']['city']})"
        )
    return "\n".join(lines)


def run_polling() -> None:
    """Simple long-polling loop. Run as `python -m app.integrations.telegram`."""
    from app.db.session import SessionLocal

    if not is_configured():
        logger.error("TELEGRAM_BOT_TOKEN is not set; nothing to poll.")
        return
    offset = 0
    logger.info("Telegram bot polling started.")
    while True:
        try:
            resp = httpx.get(
                API.format(token=settings.telegram_bot_token, method="getUpdates"),
                params={"timeout": 30, "offset": offset}, timeout=40,
            )
            for update in resp.json().get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message") or {}
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = (msg.get("text") or "").strip()
                if not chat_id or not text:
                    continue
                with SessionLocal() as db:
                    reply = _handle_query(db, text)
                send_message(chat_id, reply)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Polling error: %s", exc)
            time.sleep(3)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_polling()
