"""Use case: an authenticated user records one accessibility value (CONTRIB-01/02)."""

from __future__ import annotations

from typing import Any, Protocol

from letmegetin.core.exceptions import CriterionNotFound, PlaceNotFound
from letmegetin.domain.places.repositories import PlaceRepository
from letmegetin.domain.referential.repositories import CriterionRepository


class User(Protocol):
    """The authenticated principal the write is attributed to."""

    id: int


async def contribute(
    places: PlaceRepository,
    criteria: CriterionRepository,
    place_slug: str,
    criterion_slug: str,
    user: User,
    value: Any,
) -> None:
    """Upsert the value and append the contribution log row."""
    place = await places.get_by_slug(place_slug)
    if place is None:
        raise PlaceNotFound(place_slug)
    criterion = await criteria.get_by_slug(criterion_slug)
    if criterion is None:
        raise CriterionNotFound(criterion_slug)
    stored = {"value": value, "source": "user", "user_id": user.id}
    await places.upsert_accessibility(place.id, {criterion_slug: stored})
    await places.add_contribution(place.id, user.id, criterion.id, stored)
