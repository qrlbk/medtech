"""Prometheus metrics and request middleware."""
from __future__ import annotations

import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUESTS = Counter(
    "medprice_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
LATENCY = Histogram(
    "medprice_http_request_seconds", "HTTP request latency", ["method", "path"]
)

# Data-quality gauges, refreshed by the pipeline / a scrape hook.
DATA_FRESHNESS_RATIO = Gauge(
    "medprice_fresh_prices_ratio", "Share of active prices that are fresh (<30d)"
)
UNMATCHED_TOTAL = Gauge("medprice_unmatched_total", "Unresolved unmatched offers")
PARSER_SUCCESS = Counter(
    "medprice_parser_runs_total", "Parser runs", ["source", "status"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        # Use the route template (not the raw path) to keep cardinality low.
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
        REQUESTS.labels(request.method, path, response.status_code).inc()
        return response


def refresh_data_gauges() -> None:
    """Recompute data-quality gauges from the DB (called on each scrape)."""
    from sqlalchemy import func, select

    from app.db.session import SessionLocal
    from app.models import Price, UnmatchedQueue
    from app.services.quality import is_fresh

    try:
        with SessionLocal() as db:
            rows = db.execute(
                select(Price.parsed_at).where(Price.is_active.is_(True))
            ).scalars().all()
            if rows:
                fresh = sum(1 for p in rows if p and is_fresh(p))
                DATA_FRESHNESS_RATIO.set(round(fresh / len(rows), 4))
            unmatched = db.scalar(
                select(func.count(UnmatchedQueue.id)).where(
                    UnmatchedQueue.resolved.is_(False)
                )
            )
            UNMATCHED_TOTAL.set(unmatched or 0)
    except Exception:  # noqa: BLE001 - metrics must never break the endpoint
        pass


def metrics_endpoint() -> Response:
    refresh_data_gauges()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
