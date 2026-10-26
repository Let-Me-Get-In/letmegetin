"""Point d'entrée FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from jaccede.api import router
from jaccede.config import settings

app = FastAPI(title=settings.api_title, version=settings.api_version)
app.include_router(router)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Sonde de santé (sans dépendance base de données)."""
    return {"status": "ok"}
