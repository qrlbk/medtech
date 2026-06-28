"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import (
    routes_admin,
    routes_auth,
    routes_catalog,
    routes_meta,
    routes_search,
    routes_subscriptions,
)
from app.config import settings
from app.observability.metrics import MetricsMiddleware, metrics_endpoint

app = FastAPI(
    title="MedServicePrice.kz API",
    version=__version__,
    description="Агрегатор цен на медицинские услуги в Казахстане",
)

app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(routes_search.router, prefix=API)
app.include_router(routes_catalog.router, prefix=API)
app.include_router(routes_meta.router, prefix=API)
app.include_router(routes_auth.router, prefix=API)
app.include_router(routes_subscriptions.router, prefix=API)
app.include_router(routes_admin.router, prefix=API)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}


@app.get("/metrics", tags=["meta"])
def metrics():
    return metrics_endpoint()
