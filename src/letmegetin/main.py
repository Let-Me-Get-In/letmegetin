"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from letmegetin.api.v1.router import router
from letmegetin.config import Settings, settings

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


_validate_settings()

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


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Health probe (no database dependency)."""
    return {"status": "ok"}
