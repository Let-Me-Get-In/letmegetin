"""Use case: search places around a point (geo + text + accessibility filters)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from letmegetin.domain.places.entities import HandicapFamily, PlaceHit
from letmegetin.domain.places.repositories import PlaceRepository

DEFAULT_RADIUS_METRES = 1000.0
DEFAULT_LIMIT = 50
DEFAULT_OFFSET = 0


@dataclass(frozen=True)
class SearchPage:
    """One page of hits, plus whether another page exists after it."""

    hits: list[PlaceHit]
    has_more: bool


async def search_places(
    places: PlaceRepository,
    lat: float,
    lng: float,
    radius: float = DEFAULT_RADIUS_METRES,
    *,
    q: str | None = None,
    criterion_ids: Sequence[int] = (),
    family: HandicapFamily | None = None,
    category_id: int | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
) -> SearchPage:
    """Distance-sorted places within ``radius`` metres, narrowed by the optional filters.

    Multiple criterion ids combine with AND: a place must hold a value for every
    requested criterion. The order is total, so ``offset`` pages are disjoint.
    """
    # One extra row answers "is there another page" without a COUNT over the
    # candidate set; the repository stays a plain LIMIT/OFFSET query.
    rows = await places.list_near(
        lat,
        lng,
        radius,
        q=q,
        criterion_ids=criterion_ids,
        family=family,
        category_id=category_id,
        limit=limit + 1,
        offset=offset,
    )
    return SearchPage(hits=rows[:limit], has_more=len(rows) > limit)
