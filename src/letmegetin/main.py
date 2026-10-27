"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from letmegetin.api.v1.router import router
from letmegetin.config import settings

app = FastAPI(title=settings.api_title, version=settings.api_version)
app.include_router(router)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Health probe (no database dependency)."""
    return {"status": "ok"}
