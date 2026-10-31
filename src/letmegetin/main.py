"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from letmegetin.api.v1.router import router
from letmegetin.config import settings

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
