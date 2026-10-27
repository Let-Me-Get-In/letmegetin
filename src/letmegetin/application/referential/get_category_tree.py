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
    return build_tree(criteria)


def build_tree(criteria: list[Criterion]) -> list[Criterion]:
    """Assemble the criterion rows into their parent/children tree."""
    by_parent: dict[int | None, list[Criterion]] = {}
    for criterion in criteria:
        by_parent.setdefault(criterion.parent_id, []).append(criterion)

    def build(parent_id: int | None) -> list[Criterion]:
        return [
            replace(criterion, children=build(criterion.id))
            for criterion in by_parent.get(parent_id, [])
        ]

    return build(None)


def criterion_to_dict(criterion: Criterion) -> dict[str, object]:
    """Serialize one tree node for the precomputed ``category_grid.tree`` JSONB."""
    return {
        "slug": criterion.slug,
        "label": criterion.label,
        "description": criterion.description,
        "type": criterion.type,
        "position": criterion.position,
        "handicap_families": criterion.handicap_families,
        "en17210_ref": criterion.en17210_ref,
        "children": [criterion_to_dict(child) for child in criterion.children],
    }


def tree_to_json(tree: list[Criterion]) -> list[dict[str, object]]:
    """Serialize a whole tree, ready to be stored in ``category_grid``."""
    return [criterion_to_dict(node) for node in tree]
