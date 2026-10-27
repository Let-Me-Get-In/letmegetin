"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from letmegetin.api.v1 import referential

router = APIRouter()
router.include_router(referential.router)
