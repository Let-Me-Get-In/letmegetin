"""Use case: fetch one place with its accessibility tree, reviews and photos."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from letmegetin.core.exceptions import PlaceNotFound
from letmegetin.domain.places.entities import Place, PlaceAccessibility, PlacePhoto
from letmegetin.domain.places.repositories import PlaceRepository
from letmegetin.domain.referential.entities import HANDICAP_FAMILIES, Criterion
from letmegetin.domain.referential.repositories import (
    CategoryGridRepository,
    CriterionRepository,
)

_NON_CRITERION_TYPES = frozenset({"array", "option"})
_EMPTY_VALUES: tuple[object, ...] = (None, "", [], {})


@dataclass
class PlaceDetail:
    """A place plus its accessibility record, reviews and photos (PLACE-03/04, REV-01)."""

    place: Place
    accessibility: list[PlaceAccessibility] = field(default_factory=list)
    accessibility_by_family: dict[str, float] = field(default_factory=dict)
    tree: list[dict[str, object]] = field(default_factory=list)
    filled_rate: float = 0.0
    photos: list[PlacePhoto] = field(default_factory=list)
    rating: float | None = None
    review_count: int = 0


async def get_place(
    places: PlaceRepository,
    criteria: CriterionRepository,
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
    filled_rate = 0.0
    if place.category_slug:
        grid = await grids.get_for_slug(place.category_slug)
        if grid is not None:
            tree = _with_values(grid.tree, by_slug)
            filled_rate = _filled_rate(grid.tree, by_slug)

    rating, review_count = await places.review_stats(place.id)
    return PlaceDetail(
        place=place,
        accessibility=values,
        accessibility_by_family=_completion_by_family(
            values, {criterion.slug: criterion for criterion in await criteria.list_all()}
        ),
        tree=tree,
        filled_rate=filled_rate,
        photos=await places.list_photos(place.id),
        rating=rating,
        review_count=review_count,
    )


def _recorded(value: object) -> bool:
    """A criterion is filled when a real value is recorded (False still counts as an answer)."""
    if not isinstance(value, dict):
        return value not in _EMPTY_VALUES
    return value.get("value") not in _EMPTY_VALUES


def _leaf_slugs(nodes: list[dict[str, Any]]) -> list[str]:
    slugs: list[str] = []
    for node in nodes:
        if node.get("type") not in _NON_CRITERION_TYPES:
            slugs.append(str(node["slug"]))
        slugs.extend(_leaf_slugs(node.get("children") or []))
    return slugs


def _filled_rate(tree: list[dict[str, Any]], values: dict[str, dict[str, Any]]) -> float:
    leaves = _leaf_slugs(tree)
    if not leaves:
        return 0.0
    filled = [slug for slug in leaves if slug in values and _recorded(values[slug])]
    return round(len(set(filled)) / len(leaves), 3)


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
    values: list[PlaceAccessibility], criteria: dict[str, Criterion]
) -> dict[str, float]:
    """Share of the family's criteria the place has a positive value for."""
    satisfied = {value.criterion_slug for value in values if _recorded(value.value)}
    scores: dict[str, float] = {}
    for family in HANDICAP_FAMILIES:
        family_criteria = [
            slug for slug, criterion in criteria.items() if family in criterion.handicap_families
        ]
        scores[family] = (
            round(len(satisfied.intersection(family_criteria)) / len(family_criteria), 3)
            if family_criteria
            else 0.0
        )
    return scores
