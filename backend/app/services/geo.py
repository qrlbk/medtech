"""Geo-enrichment of clinics via 2GIS / Google Maps (ТЗ: 2gis.kz / Google Maps).

Fills clinic address, working hours, phone and lat/lon. A live provider is used
only when its API key is configured:

- ``DGIS_API_KEY``        -> 2GIS Catalog API (https://docs.2gis.com)
- ``GOOGLE_MAPS_API_KEY`` -> Google Places API

When no key is set (or a request fails), the function returns ``None`` and the
caller falls back to the bundled ``clinics.json`` seed, so the app stays fully
functional offline.
"""
from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

_DGIS_URL = "https://catalog.api.2gis.com/3.0/items"
_GOOGLE_FIND = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
_GOOGLE_DETAILS = "https://maps.googleapis.com/maps/api/place/details/json"
_TIMEOUT = 8.0

_DAYS_RU = {
    "Mon": "Пн", "Tue": "Вт", "Wed": "Ср", "Thu": "Чт",
    "Fri": "Пт", "Sat": "Сб", "Sun": "Вс",
}


def geocode_clinic(name: str, city: str | None) -> dict | None:
    """Return clinic geo metadata from a live provider, or ``None``.

    Result keys (any may be missing): ``address``, ``lat``, ``lon``,
    ``working_hours``, ``phone``, ``provider``.
    """
    query = f"{name} {city}".strip() if city else name
    for provider in (_from_2gis, _from_google):
        try:
            data = provider(query)
        except Exception as exc:  # noqa: BLE001 - geo is best-effort
            logger.warning("Geo provider %s failed for %r: %s",
                           provider.__name__, query, exc)
            continue
        if data:
            return data
    return None


def _from_2gis(query: str) -> dict | None:
    key = os.getenv("DGIS_API_KEY")
    if not key:
        return None
    params = {
        "q": query,
        "fields": ("items.point,items.address,items.schedule,"
                   "items.contact_groups"),
        "key": key,
        "page_size": 1,
    }
    resp = requests.get(_DGIS_URL, params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    items = (resp.json().get("result") or {}).get("items") or []
    if not items:
        return None
    item = items[0]
    point = item.get("point") or {}
    return {
        "address": item.get("address_name"),
        "lat": point.get("lat"),
        "lon": point.get("lon"),
        "working_hours": _fmt_2gis_schedule(item.get("schedule")),
        "phone": _first_2gis_phone(item.get("contact_groups")),
        "provider": "2gis",
    }


def _from_google(query: str) -> dict | None:
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        return None
    find = requests.get(_GOOGLE_FIND, timeout=_TIMEOUT, params={
        "input": query,
        "inputtype": "textquery",
        "fields": "place_id,geometry,formatted_address",
        "language": "ru",
        "key": key,
    })
    find.raise_for_status()
    candidates = find.json().get("candidates") or []
    if not candidates:
        return None
    top = candidates[0]
    loc = (top.get("geometry") or {}).get("location") or {}
    result = {
        "address": top.get("formatted_address"),
        "lat": loc.get("lat"),
        "lon": loc.get("lng"),
        "provider": "google",
    }
    place_id = top.get("place_id")
    if place_id:
        det = requests.get(_GOOGLE_DETAILS, timeout=_TIMEOUT, params={
            "place_id": place_id,
            "fields": "opening_hours,formatted_phone_number",
            "language": "ru",
            "key": key,
        })
        if det.ok:
            d = det.json().get("result") or {}
            result["phone"] = d.get("formatted_phone_number")
            hours = (d.get("opening_hours") or {}).get("weekday_text")
            if hours:
                result["working_hours"] = "; ".join(hours)
    return result


def _fmt_2gis_schedule(schedule: dict | None) -> str | None:
    if not schedule:
        return None
    parts = []
    for eng, ru in _DAYS_RU.items():
        day = schedule.get(eng.lower()) or schedule.get(eng)
        hours = (day or {}).get("working_hours") if isinstance(day, dict) else None
        if hours:
            first = hours[0]
            parts.append(f"{ru} {first.get('from')}-{first.get('to')}")
    return ", ".join(parts) or None


def _first_2gis_phone(contact_groups: list | None) -> str | None:
    for group in contact_groups or []:
        for contact in group.get("contacts", []):
            if contact.get("type") == "phone":
                return contact.get("text") or contact.get("value")
    return None
