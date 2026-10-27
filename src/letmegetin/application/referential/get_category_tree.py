"""Use case: build the accessibility criteria tree for a category."""

from __future__ import annotations

from dataclasses import replace

from letmegetin.core.exceptions import CategoryNotFound
from letmegetin.domain.referential.entities import Criterion
from letmegetin.domain.referential.repositories import (
    CategoryRepository,
    CriterionRepository,
)


async def get_category_tree(
    category_repository: CategoryRepository,
    criterion_repository: CriterionRepository,
    slug: str,
) -> list[Criterion]:
    """Return the root criteria (with descendants) applicable to a category."""
    category = await category_repository.get_by_slug(slug)
    if category is None:
        raise CategoryNotFound(slug)
    criteria = await criterion_repository.list_for_category(category.id)
    return _build_tree(criteria)


def _build_tree(criteria: list[Criterion]) -> list[Criterion]:
    by_parent: dict[int | None, list[Criterion]] = {}
    for criterion in criteria:
        by_parent.setdefault(criterion.parent_id, []).append(criterion)

    def build(parent_id: int | None) -> list[Criterion]:
        return [
            replace(criterion, children=build(criterion.id))
            for criterion in by_parent.get(parent_id, [])
        ]

    return build(None)
