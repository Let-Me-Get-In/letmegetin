"""Referential API v1 endpoints (presentation layer)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from letmegetin.api.deps import (
    CategoryGridRepo,
    CategoryRepo,
    CriterionRepo,
    FilterRepo,
    OtherInformationRepo,
    public_rate_limit,
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
from letmegetin.core.cache import get_cache
from letmegetin.core.exceptions import CategoryNotFound
from letmegetin.domain.referential.entities import Criterion

router = APIRouter(
    prefix="/api/v1", tags=["referential"], dependencies=[Depends(public_rate_limit)]
)


@router.get("/categories", response_model=list[CategoryOut])
async def get_categories(repository: CategoryRepo, grids: CategoryGridRepo) -> list[CategoryOut]:
    """List every place category (cached by referential version)."""
    version = await grids.current_version()
    cache = get_cache()
    key = f"ref:{version}:categories"
    cached = await cache.get_json(key)
    if cached is not None:
        return [CategoryOut.model_validate(item) for item in cached]
    categories = [
        CategoryOut.model_validate(category) for category in await list_categories(repository)
    ]
    await cache.set_json(key, [category.model_dump() for category in categories])
    return categories


@router.get("/categories/{slug}/criteria", response_model=list[CriterionOut])
async def get_criteria(
    slug: str, categories: CategoryRepo, criteria: CriterionRepo, grids: CategoryGridRepo
) -> list[CriterionOut]:
    """Return the accessibility criteria tree for a category (cached by version)."""
    version = await grids.current_version()
    cache = get_cache()
    key = f"ref:{version}:criteria:{slug}"
    cached = await cache.get_json(key)
    if cached is not None:
        return [CriterionOut.model_validate(item) for item in cached]
    try:
        tree = await get_category_tree(categories, criteria, slug)
    except CategoryNotFound:
        raise HTTPException(status_code=404, detail="Category not found") from None
    payload = [_to_out(node).model_dump() for node in tree]
    await cache.set_json(key, payload)
    return [CriterionOut.model_validate(item) for item in payload]


def _to_out(node: Criterion) -> CriterionOut:
    return CriterionOut(
        id=node.id,
        slug=node.slug,
        label=node.label,
        description=node.description,
        type=node.type,
        handicap_families=node.handicap_families,
        en17210_ref=node.en17210_ref,
        children=[_to_out(child) for child in node.children],
    )


@router.get("/categories/{slug}/grid")
async def get_category_grid(slug: str, request: Request, repository: CategoryGridRepo) -> Response:
    """Return the precomputed criteria grid, cached by the global referential version."""
    version = await repository.current_version()
    cache = get_cache()
    cached = await cache.get_json(f"ref:{version}:grid:{slug}")
    if cached is not None:
        etag = f'W/"ref-{version}"'
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        return JSONResponse(
            {"category": slug, "version": version, "tree": cached},
            headers={"ETag": etag, "Cache-Control": "public, max-age=300"},
        )
    grid = await repository.get_for_slug(slug)
    if grid is None:
        raise HTTPException(status_code=404, detail="Category grid not found")
    await cache.set_json(f"ref:{grid.version}:grid:{slug}", grid.tree)
    etag = f'W/"ref-{grid.version}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return JSONResponse(
        {"category": grid.category_slug, "version": grid.version, "tree": grid.tree},
        headers={"ETag": etag, "Cache-Control": "public, max-age=300"},
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
