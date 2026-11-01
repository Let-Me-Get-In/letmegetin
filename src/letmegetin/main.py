"""FastAPI application entry point."""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request, Response

from letmegetin.api.v1.router import router
from letmegetin.config import Settings, settings
from letmegetin.core.metrics import REDIS_UP, record_request, render_metrics
from letmegetin.core.observability import init_sentry
from letmegetin.core.redis import get_redis

logger = logging.getLogger(__name__)
DEFAULT_JWT_SECRET = Settings.model_fields["jwt_secret"].default


def _validate_settings() -> None:
    """Fail fast on the development secret in production; warn on missing Redis."""
    if settings.environment == "production" and settings.jwt_secret == DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "LETMEGETIN_JWT_SECRET must be set when LETMEGETIN_ENVIRONMENT=production"
        )
    if settings.environment == "production" and not settings.redis_url:
        logger.warning("No LETMEGETIN_REDIS_URL: limits are per worker and the cache is disabled")
    if settings.environment == "production" and not settings.sentry_dsn:
        logger.warning("No LETMEGETIN_SENTRY_DSN: errors are only visible in logs/metrics")


_validate_settings()
init_sentry()

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=(
        "Open accessibility referential: places, categories, typed criteria, "
        "contributions and reviews. Public reads accept an optional X-API-Key "
        "for a dedicated rate limit; writes require a bearer token."
    ),
    openapi_tags=[
        {"name": "places", "description": "Search, detail, contributions and reviews."},
        {"name": "referential", "description": "Categories, criteria trees, filters and grids."},
        {"name": "auth", "description": "Accounts, sessions and email verification."},
        {"name": "ops", "description": "Health probe."},
    ],
)
app.include_router(router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched")
    record_request(request.method, path, response.status_code, time.perf_counter() - started)
    return response


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus payload; internal network only (Caddy blocks it)."""
    client = get_redis()
    if client is None:
        REDIS_UP.set(0)
    else:
        try:
            await client.ping()
            REDIS_UP.set(1)
        except Exception:  # noqa: BLE001 - a metric must never fail the scrape
            REDIS_UP.set(0)
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Health probe (no database dependency)."""
    return {"status": "ok"}
