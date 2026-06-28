"""Polite HTTP client: rate limiting, UA rotation, robots.txt, retries.

Implements the ТЗ rules: do not overload sources (delays between requests),
respect robots.txt, only fetch public pages.
"""
from __future__ import annotations

import logging
import os
import random
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests
import urllib3
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Many KZ medical sites serve incomplete TLS chains (missing intermediates), so
# strict verification fails even though the site is legitimate and public. We
# fall back to an unverified request in that case (public data only), and mute
# the resulting noise from urllib3.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0 Safari/537.36",
]


class PoliteClient:
    """Throttled requests session that honours robots.txt per host."""

    def __init__(self, crawl_delay: float = 1.5, respect_robots: bool = True,
                 timeout: float = 8.0, verify: bool | None = None) -> None:
        self.crawl_delay = crawl_delay
        self.respect_robots = respect_robots
        self.timeout = timeout
        # TLS verification on by default; MEDPRICE_TLS_VERIFY=0 disables globally.
        self.verify = (
            os.getenv("MEDPRICE_TLS_VERIFY", "1") not in {"0", "false", "False"}
            if verify is None else verify
        )
        self._last_request_at: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._session = requests.Session()

    def _robots_for(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        if not self.respect_robots:
            return None
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{host}/robots.txt")
            try:
                rp.read()
            except Exception as exc:  # noqa: BLE001 - robots fetch is best-effort
                logger.warning("robots.txt fetch failed for %s: %s", host, exc)
                rp = None  # type: ignore[assignment]
            self._robots[host] = rp  # type: ignore[assignment]
        return self._robots[host]

    def can_fetch(self, url: str, ua: str) -> bool:
        rp = self._robots_for(url)
        if rp is None:
            return True
        return rp.can_fetch(ua, url)

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            wait = self.crawl_delay - elapsed
            if wait > 0:
                time.sleep(wait + random.uniform(0, 0.4))
        self._last_request_at[host] = time.monotonic()

    @retry(stop=stop_after_attempt(2),
           wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
    def get(self, url: str) -> str:
        ua = random.choice(_USER_AGENTS)
        if not self.can_fetch(url, ua):
            raise PermissionError(f"robots.txt disallows fetching {url}")
        self._throttle(url)
        headers = {"User-Agent": ua, "Accept-Language": "ru,kk;q=0.8,en;q=0.5"}
        try:
            resp = self._session.get(
                url, headers=headers, timeout=self.timeout, verify=self.verify
            )
        except requests.exceptions.SSLError:
            # Incomplete cert chain on the source: retry once without verifying.
            logger.warning("TLS verification failed for %s; retrying unverified", url)
            resp = self._session.get(
                url, headers=headers, timeout=self.timeout, verify=False
            )
        resp.raise_for_status()
        return resp.text
