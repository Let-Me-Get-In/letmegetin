"""Use case: read a place's published reviews, paginated (REV-01)."""

from __future__ import annotations

from dataclasses import dataclass, field

from letmegetin.core.exceptions import PlaceNotFound
from letmegetin.domain.places.entities import Review
from letmegetin.domain.places.repositories import PlaceRepository


@dataclass
class ReviewPage:
    """One page of reviews plus the total count."""

    items: list[Review] = field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20


async def list_reviews(places: PlaceRepository, slug: str, *, page: int, size: int) -> ReviewPage:
    """Return the requested page, or raise ``PlaceNotFound``."""
    place = await places.get_by_slug(slug)
    if place is None:
        raise PlaceNotFound(slug)
    items, total = await places.list_reviews(place.id, page=page, size=size)
    return ReviewPage(items=items, total=total, page=page, size=size)
