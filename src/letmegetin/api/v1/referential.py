"""Referential API v1 endpoints (presentation layer)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from letmegetin.api.deps import (
    CategoryRepo,
    CriterionRepo,
    FilterRepo,
    OtherInformationRepo,
)
from letmegetin.api.schemas.referential import (
    CategoryOut,
    CriterionOut,
    FilterOut,
    OtherInformationOut,
)
from letmegetin.application.referential.get_category_tree import get_category_tree
from letmegetin.application.referential.list_categories import list_categories
from letmegetin.application.referential.list_filters import list_filters
from letmegetin.application.referential.list_other_information import list_other_information
from letmegetin.core.exceptions import CategoryNotFound
from letmegetin.domain.referential.entities import Criterion

router = APIRouter(prefix="/api/v1", tags=["referential"])


@router.get("/categories", response_model=list[CategoryOut])
async def get_categories(repository: CategoryRepo) -> list[CategoryOut]:
    """List every place category."""
    return [CategoryOut.model_validate(category) for category in await list_categories(repository)]


@router.get("/categories/{slug}/criteria", response_model=list[CriterionOut])
async def get_criteria(
    slug: str, categories: CategoryRepo, criteria: CriterionRepo
) -> list[CriterionOut]:
    """Return the accessibility criteria tree for a category."""
    try:
        tree = await get_category_tree(categories, criteria, slug)
    except CategoryNotFound:
        raise HTTPException(status_code=404, detail="Category not found") from None
    return [_to_out(node) for node in tree]


def _to_out(node: Criterion) -> CriterionOut:
    return CriterionOut(
        slug=node.slug,
        label=node.label,
        description=node.description,
        type=node.type,
        children=[_to_out(child) for child in node.children],
    )


@router.get("/filters", response_model=list[FilterOut])
async def get_filters(repository: FilterRepo) -> list[FilterOut]:
    """List the active accessibility filters."""
    return [FilterOut.model_validate(item) for item in await list_filters(repository)]


@router.get("/other-information", response_model=list[OtherInformationOut])
async def get_other_information(repository: OtherInformationRepo) -> list[OtherInformationOut]:
    """List official labels / complementary information."""
    items = await list_other_information(repository)
    return [OtherInformationOut.model_validate(item) for item in items]
