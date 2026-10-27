"""Use cases: create and moderate reviews (REV-02, AUTH-03)."""

from __future__ import annotations

from typing import Protocol

from letmegetin.core.exceptions import PlaceNotFound, ReviewNotFound
from letmegetin.domain.places.entities import Review
from letmegetin.domain.places.repositories import PlaceRepository


class User(Protocol):
    """The authenticated principal writing or moderating the review."""

    id: int
    display_name: str | None


async def create_review(
    places: PlaceRepository,
    place_slug: str,
    user: User,
    rating: int,
    body: str,
) -> Review:
    """Create a published review attributed to the user's display name (never the email)."""
    place = await places.get_by_slug(place_slug)
    if place is None:
        raise PlaceNotFound(place_slug)
    return await places.add_review(
        place.id,
        user.id,
        rating,
        body,
        user.display_name or "Anonyme",
    )


async def set_review_status(places: PlaceRepository, review_id: int, status: str) -> Review:
    """Hide or restore a review (admin only)."""
    review = await places.set_review_status(review_id, status)
    if review is None:
        raise ReviewNotFound(review_id)
    return review
