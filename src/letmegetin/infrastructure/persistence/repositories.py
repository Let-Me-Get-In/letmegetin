"""SQLAlchemy implementations of the referential repository ports."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.referential.entities import (
    AccessibilityFilter,
    Category,
    Criterion,
    OtherInformation,
    VocabularyEntry,
)
from letmegetin.domain.referential.repositories import MappingState
from letmegetin.infrastructure.persistence.mappers import (
    category_from_model,
    criterion_from_model,
    filter_from_model,
    other_information_from_model,
    vocabulary_from_model,
)
from letmegetin.infrastructure.persistence.models import (
    AccessibilityFilterModel,
    CategoryCriterionModel,
    CategoryModel,
    CriterionModel,
    CriterionVocabularyModel,
    OtherInformationModel,
)


class SqlAlchemyCategoryRepository:
    """Category repository backed by SQLAlchemy (no commit: the caller owns the unit of work)."""

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

    async def add(self, category: Category) -> Category:
        model = CategoryModel(
            slug=category.slug,
            name=category.name,
            label=category.label,
            parent_id=category.parent_id,
        )
        self._session.add(model)
        await self._session.flush()
        return category_from_model(model)

    async def update(self, category: Category) -> Category:
        model = await self._session.get(CategoryModel, category.id)
        if model is None:
            raise DomainError(f"category '{category.slug}' is not persisted")
        model.slug = category.slug
        model.name = category.name
        model.label = category.label
        model.parent_id = category.parent_id
        await self._session.flush()
        return category_from_model(model)


class SqlAlchemyCriterionRepository:
    """Criterion repository backed by SQLAlchemy (no commit: the caller owns the unit of work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_category(self, category_id: int) -> list[Criterion]:
        rows = list(
            (
                await self._session.scalars(
                    select(CriterionModel).order_by(CriterionModel.position)
                )
            ).all()
        )
        links = (
            await self._session.scalars(
                select(CategoryCriterionModel).where(
                    CategoryCriterionModel.category_id == category_id
                )
            )
        ).all()
        by_id = {row.id: row for row in rows}
        excluded = {link.criterion_id for link in links if link.excluded}
        included = {link.criterion_id for link in links if not link.excluded}
        resolved = {row.id for row in rows if row.is_default and row.id not in excluded}
        resolved |= included

        children: dict[int | None, list[int]] = {}
        for row in rows:
            children.setdefault(row.parent_id, []).append(row.id)

        keep = set(resolved)
        stack = list(resolved)
        while stack:
            for child_id in children.get(stack.pop(), []):
                if child_id not in keep:
                    keep.add(child_id)
                    stack.append(child_id)

        for criterion_id in list(keep):
            current = by_id.get(criterion_id)
            while current is not None and current.parent_id is not None:
                keep.add(current.parent_id)
                current = by_id.get(current.parent_id)

        return [criterion_from_model(row) for row in rows if row.id in keep]

    async def list_all(self) -> list[Criterion]:
        rows = (
            await self._session.scalars(
                select(CriterionModel).order_by(CriterionModel.parent_id, CriterionModel.position)
            )
        ).all()
        return [criterion_from_model(row) for row in rows]

    async def get_by_slug(self, slug: str) -> Criterion | None:
        row = await self._session.scalar(select(CriterionModel).where(CriterionModel.slug == slug))
        return criterion_from_model(row) if row is not None else None

    async def add(self, criterion: Criterion) -> Criterion:
        model = CriterionModel(
            slug=criterion.slug,
            parent_id=criterion.parent_id,
            type=criterion.type,
            position=criterion.position,
            label=criterion.label,
            description=criterion.description,
            is_default=criterion.is_default,
        )
        self._session.add(model)
        await self._session.flush()
        return criterion_from_model(model)

    async def update(self, criterion: Criterion) -> Criterion:
        model = await self._session.get(CriterionModel, criterion.id)
        if model is None:
            raise DomainError(f"criterion '{criterion.slug}' is not persisted")
        model.slug = criterion.slug
        model.parent_id = criterion.parent_id
        model.type = criterion.type
        model.position = criterion.position
        model.label = criterion.label
        model.description = criterion.description
        model.is_default = criterion.is_default
        await self._session.flush()
        return criterion_from_model(model)


class SqlAlchemyMappingRepository:
    """Category-to-criterion mapping repository (no commit: the caller owns the unit of work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set_state(self, category_id: int, criterion_id: int, state: MappingState) -> None:
        model = await self._session.get(CategoryCriterionModel, (category_id, criterion_id))
        if state == "clear":
            if model is not None:
                await self._session.delete(model)
                await self._session.flush()
            return
        excluded = state == "exclude"
        if model is not None:
            model.excluded = excluded
        else:
            self._session.add(
                CategoryCriterionModel(
                    category_id=category_id, criterion_id=criterion_id, excluded=excluded
                )
            )
        await self._session.flush()


class SqlAlchemyVocabularyRepository:
    """Vocabulary repository backed by SQLAlchemy (no commit: the caller owns the unit of work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[VocabularyEntry]:
        rows = (
            await self._session.scalars(
                select(CriterionVocabularyModel).order_by(CriterionVocabularyModel.slug)
            )
        ).all()
        return [vocabulary_from_model(row) for row in rows]

    async def get_by_slug(self, slug: str) -> VocabularyEntry | None:
        row = await self._session.scalar(
            select(CriterionVocabularyModel).where(CriterionVocabularyModel.slug == slug)
        )
        return vocabulary_from_model(row) if row is not None else None

    async def add(self, entry: VocabularyEntry) -> VocabularyEntry:
        model = CriterionVocabularyModel(
            slug=entry.slug,
            label=entry.label,
            description=entry.description,
            promoted_criterion_id=entry.promoted_criterion_id,
        )
        self._session.add(model)
        await self._session.flush()
        return vocabulary_from_model(model)

    async def update(self, entry: VocabularyEntry) -> VocabularyEntry:
        model = await self._session.get(CriterionVocabularyModel, entry.id)
        if model is None:
            raise DomainError(f"vocabulary entry '{entry.slug}' is not persisted")
        model.slug = entry.slug
        model.label = entry.label
        model.description = entry.description
        model.promoted_criterion_id = entry.promoted_criterion_id
        await self._session.flush()
        return vocabulary_from_model(model)


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
