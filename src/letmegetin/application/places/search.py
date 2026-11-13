"""Use case: search places around a point (geo + text + accessibility filters)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from letmegetin.domain.places.documentation import Documentation, filled_rate
from letmegetin.domain.places.entities import HandicapFamily, PlaceHit
from letmegetin.domain.places.repositories import PlaceRepository
from letmegetin.domain.referential.repositories import CategoryGridRepository

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
    grids: CategoryGridRepository,
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
    with_documentation: bool = False,
) -> SearchPage:
    """Distance-sorted places within ``radius`` metres, narrowed by the optional filters.

    Multiple criterion ids combine with AND: a place must hold a value for every
    requested criterion. The order is total, so ``offset`` pages are disjoint.
    ``with_documentation`` is opt-in: it costs two batched reads over the hit set and
    is absent from the response otherwise (D-07).
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
    hits = rows[:limit]
    if with_documentation:
        await _attach_documentation(grids, places, hits)
    return SearchPage(hits=hits, has_more=len(rows) > limit)


async def _attach_documentation(
    grids: CategoryGridRepository, places: PlaceRepository, hits: list[PlaceHit]
) -> None:
    """Fill each hit's documentation from two reads over the whole hit set.

    The grid tree is read per distinct category and the values per place id, so the
    query count does not grow with the page size. A hit with no grid or no recorded
    value is simply undocumented — ``filled_rate`` answers 0.0 and the level is
    ``none``; no hit is dropped (D-06).
    """
    slugs = list(dict.fromkeys(hit.place.category_slug for hit in hits if hit.place.category_slug))
    grids_by_slug = await grids.get_for_slugs(slugs)
    values_by_place = await places.list_accessibility_for_places([hit.place.id for hit in hits])
    for hit in hits:
        grid = grids_by_slug.get(hit.place.category_slug or "")
        values = {
            value.criterion_slug: value.value for value in values_by_place.get(hit.place.id, [])
        }
        hit.documentation = Documentation.from_rate(
            filled_rate(grid.tree, values) if grid is not None else 0.0
        )
