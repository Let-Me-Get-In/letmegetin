"""Use case: search places around a point (geo + text + accessibility filters)."""

from __future__ import annotations

from collections.abc import Sequence

from letmegetin.domain.places.entities import HandicapFamily, PlaceHit
from letmegetin.domain.places.repositories import PlaceRepository

DEFAULT_RADIUS_METRES = 1000.0
DEFAULT_LIMIT = 50


async def search_places(
    places: PlaceRepository,
    lat: float,
    lng: float,
    radius: float = DEFAULT_RADIUS_METRES,
    *,
    q: str | None = None,
    criterion_ids: Sequence[int] = (),
    family: HandicapFamily | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[PlaceHit]:
    """Distance-sorted places within ``radius`` metres, optionally filtered."""
    return await places.list_near(
        lat,
        lng,
        radius,
        q=q,
        criterion_ids=criterion_ids,
        family=family,
        limit=limit,
    )
