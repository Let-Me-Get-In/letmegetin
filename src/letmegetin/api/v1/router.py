"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from letmegetin.api.v1 import places, referential

router = APIRouter()
router.include_router(referential.router)
router.include_router(places.router)
