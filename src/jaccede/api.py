"""Routes de l'API v1 (référentiel)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jaccede.db import get_session
from jaccede.models import (
    AccessibilityFilter,
    Category,
    CategoryCriterion,
    Criterion,
    OtherInformation,
)
from jaccede.schemas import CategoryOut, CriterionOut, FilterOut, OtherInformationOut

router = APIRouter(prefix="/api/v1", tags=["referential"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(session: AsyncSession = Depends(get_session)) -> list[Category]:
    """Liste toutes les catégories de lieux."""
    return list((await session.scalars(select(Category).order_by(Category.slug))).all())


@router.get("/categories/{slug}/criteria", response_model=list[CriterionOut])
async def category_criteria(
    slug: str, session: AsyncSession = Depends(get_session)
) -> list[CriterionOut]:
    """Arbre d'accessibilité applicable à une catégorie."""
    category = await session.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    linked = set(
        (
            await session.scalars(
                select(CategoryCriterion.criterion_id).where(
                    CategoryCriterion.category_id == category.id
                )
            )
        ).all()
    )
    criteria = list((await session.scalars(select(Criterion).order_by(Criterion.position))).all())
    by_id = {criterion.id: criterion for criterion in criteria}

    keep: set[int] = set()
    for criterion_id in linked:
        current = by_id.get(criterion_id)
        while current is not None:
            keep.add(current.id)
            current = by_id.get(current.parent_id) if current.parent_id else None

    roots = [c for c in criteria if c.parent_id is None and c.id in keep]
    return [_to_tree(root, criteria) for root in roots]


def _to_tree(node: Criterion, criteria: list[Criterion]) -> CriterionOut:
    children = [_to_tree(child, criteria) for child in criteria if child.parent_id == node.id]
    return CriterionOut(
        slug=node.slug,
        label=node.label,
        description=node.description,
        type=node.type,
        children=children,
    )


@router.get("/filters", response_model=list[FilterOut])
async def list_filters(session: AsyncSession = Depends(get_session)) -> list[AccessibilityFilter]:
    """Filtres d'accessibilité disponibles en recherche."""
    return list(
        (
            await session.scalars(
                select(AccessibilityFilter)
                .where(AccessibilityFilter.active.is_(True))
                .order_by(AccessibilityFilter.position)
            )
        ).all()
    )


@router.get("/other-information", response_model=list[OtherInformationOut])
async def list_other_information(
    session: AsyncSession = Depends(get_session),
) -> list[OtherInformation]:
    """Labels officiels (ex. Tourisme & Handicap)."""
    return list(
        (await session.scalars(select(OtherInformation).order_by(OtherInformation.name))).all()
    )
