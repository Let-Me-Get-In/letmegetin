"""SQLAlchemy implementations of the referential repository ports."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.domain.referential.entities import (
    AccessibilityFilter,
    Category,
    Criterion,
    OtherInformation,
)
from letmegetin.infrastructure.persistence.mappers import (
    category_from_model,
    criterion_from_model,
    filter_from_model,
    other_information_from_model,
)
from letmegetin.infrastructure.persistence.models import (
    AccessibilityFilterModel,
    CategoryCriterionModel,
    CategoryModel,
    CriterionModel,
    OtherInformationModel,
)


class SqlAlchemyCategoryRepository:
    """Category read repository backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Category]:
        rows = (
            await self._session.scalars(select(CategoryModel).order_by(CategoryModel.slug))
        ).all()
        return [category_from_model(row) for row in rows]

    async def get_by_slug(self, slug: str) -> Category | None:
        row = await self._session.scalar(select(CategoryModel).where(CategoryModel.slug == slug))
        return category_from_model(row) if row is not None else None


class SqlAlchemyCriterionRepository:
    """Criterion read repository backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_category(self, category_id: int) -> list[Criterion]:
        linked = set(
            (
                await self._session.scalars(
                    select(CategoryCriterionModel.criterion_id).where(
                        CategoryCriterionModel.category_id == category_id
                    )
                )
            ).all()
        )
        rows = list(
            (
                await self._session.scalars(
                    select(CriterionModel).order_by(CriterionModel.position)
                )
            ).all()
        )
        by_id = {row.id: row for row in rows}
        keep: set[int] = set()
        for criterion_id in linked:
            current = by_id.get(criterion_id)
            while current is not None:
                keep.add(current.id)
                current = by_id.get(current.parent_id) if current.parent_id else None
        return [criterion_from_model(row) for row in rows if row.id in keep]


class SqlAlchemyFilterRepository:
    """Filter read repository backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[AccessibilityFilter]:
        rows = (
            await self._session.scalars(
                select(AccessibilityFilterModel)
                .where(AccessibilityFilterModel.active.is_(True))
                .order_by(AccessibilityFilterModel.position)
            )
        ).all()
        return [filter_from_model(row) for row in rows]


class SqlAlchemyOtherInformationRepository:
    """Official-label read repository backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[OtherInformation]:
        rows = (
            await self._session.scalars(
                select(OtherInformationModel).order_by(OtherInformationModel.name)
            )
        ).all()
        return [other_information_from_model(row) for row in rows]
