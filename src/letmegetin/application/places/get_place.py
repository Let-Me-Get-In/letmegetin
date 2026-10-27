"""Use case: fetch one place with its accessibility values and per-family scores."""

from __future__ import annotations

from dataclasses import dataclass, field

from letmegetin.core.exceptions import PlaceNotFound
from letmegetin.domain.places.entities import Place, PlaceAccessibility
from letmegetin.domain.places.repositories import PlaceRepository
from letmegetin.domain.referential.entities import HANDICAP_FAMILIES, Criterion
from letmegetin.domain.referential.repositories import CriterionRepository


@dataclass
class PlaceDetail:
    """A place plus its accessibility record (PLACE-03/04)."""

    place: Place
    accessibility: list[PlaceAccessibility] = field(default_factory=list)
    accessibility_by_family: dict[str, float] = field(default_factory=dict)


async def get_place(
    places: PlaceRepository, criteria: CriterionRepository, slug: str
) -> PlaceDetail:
    """Return the place detail, or raise ``PlaceNotFound``."""
    place = await places.get_by_slug(slug)
    if place is None:
        raise PlaceNotFound(slug)
    values = await places.list_accessibility(place.id)
    return PlaceDetail(
        place=place,
        accessibility=values,
        accessibility_by_family=_completion_by_family(
            values, {criterion.slug: criterion for criterion in await criteria.list_all()}
        ),
    )


def _completion_by_family(
    values: list[PlaceAccessibility], criteria: dict[str, Criterion]
) -> dict[str, float]:
    """Share of the family's criteria the place has a positive value for."""
    satisfied = {
        value.criterion_slug
        for value in values
        if (value.value or {}).get("value") not in (None, False, "", [], {})
    }
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
