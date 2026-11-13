"""Use case: fetch one place with its accessibility tree, reviews and photos."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from letmegetin.core.exceptions import PlaceNotFound
from letmegetin.domain.places.documentation import (
    Documentation,
    answerable_criteria,
    filled_rate,
    recorded,
)
from letmegetin.domain.places.entities import Place, PlaceAccessibility, PlacePhoto
from letmegetin.domain.places.repositories import PlaceRepository
from letmegetin.domain.referential.entities import HANDICAP_FAMILIES
from letmegetin.domain.referential.repositories import CategoryGridRepository


@dataclass
class PlaceDetail:
    """A place plus its accessibility record, reviews and photos (PLACE-03/04, REV-01)."""

    place: Place
    accessibility: list[PlaceAccessibility] = field(default_factory=list)
    accessibility_by_family: dict[str, float] = field(default_factory=dict)
    tree: list[dict[str, object]] = field(default_factory=list)
    filled_rate: float = 0.0
    documentation: Documentation | None = None
    photos: list[PlacePhoto] = field(default_factory=list)
    rating: float | None = None
    review_count: int = 0


async def get_place(
    places: PlaceRepository,
    grids: CategoryGridRepository,
    slug: str,
) -> PlaceDetail:
    """Return the place detail, or raise ``PlaceNotFound``."""
    place = await places.get_by_slug(slug)
    if place is None:
        raise PlaceNotFound(slug)

    values = await places.list_accessibility(place.id)
    by_slug = {value.criterion_slug: value.value for value in values}
    tree: list[dict[str, object]] = []
    rate = 0.0
    leaves: dict[str, list[str]] = {}
    if place.category_slug:
        grid = await grids.get_for_slug(place.category_slug)
        if grid is not None:
            tree = _with_values(grid.tree, by_slug)
            rate = filled_rate(grid.tree, by_slug)
            leaves = {
                str(node["slug"]): list(node.get("handicap_families") or [])
                for node in answerable_criteria(grid.tree)
            }

    rating, review_count = await places.review_stats(place.id)
    return PlaceDetail(
        place=place,
        accessibility=values,
        accessibility_by_family=_completion_by_family(values, leaves),
        tree=tree,
        filled_rate=rate,
        documentation=Documentation.from_rate(rate),
        photos=await places.list_photos(place.id),
        rating=rating,
        review_count=review_count,
    )


def _with_values(
    nodes: list[dict[str, Any]], values: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Copy the grid tree, adding the recorded value (or null) to every node."""
    return [
        {
            **node,
            "value": values.get(str(node["slug"])),
            "children": _with_values(node.get("children") or [], values),
        }
        for node in nodes
    ]


def _completion_by_family(
    values: list[PlaceAccessibility], leaves: dict[str, list[str]]
) -> dict[str, float]:
    """Share of the family's answerable grid leaves the place carries a value for.

    A family with no leaf in this place's grid is omitted rather than reported as 0.0:
    "no criterion to answer" is not "not documented" (D-12).
    """
    satisfied = {value.criterion_slug for value in values if recorded(value.value)}
    scores: dict[str, float] = {}
    for family in HANDICAP_FAMILIES:
        family_leaves = [slug for slug, families in leaves.items() if family in families]
        if not family_leaves:
            continue
        scores[family] = round(len(satisfied.intersection(family_leaves)) / len(family_leaves), 3)
    return scores
