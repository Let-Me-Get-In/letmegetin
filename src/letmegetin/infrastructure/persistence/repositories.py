"""SQLAlchemy implementations of the referential repository ports."""

from __future__ import annotations

from collections.abc import Sequence

from geoalchemy2 import Geography
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.dedup import normalize_name
from letmegetin.domain.places.entities import HandicapFamily, Place, PlaceAccessibility, PlaceHit
from letmegetin.domain.places.repositories import DEFAULT_CANDIDATE_RADIUS
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
    place_accessibility_from_models,
    place_from_model,
    vocabulary_from_model,
)
from letmegetin.infrastructure.persistence.models import (
    AccessibilityFilterModel,
    CategoryCriterionModel,
    CategoryMappingModel,
    CategoryModel,
    CriterionModel,
    CriterionVocabularyModel,
    OtherInformationModel,
    PlaceAccessibilityModel,
    PlaceAliasModel,
    PlaceMergeLogModel,
    PlaceModel,
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
            handicap_families=criterion.handicap_families,
            en17210_ref=criterion.en17210_ref,
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
        model.handicap_families = criterion.handicap_families
        model.en17210_ref = criterion.en17210_ref
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


def _point(lat: float, lng: float) -> object:
    """A geography point built from bound parameters (never from interpolated SQL)."""
    return func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326).cast(Geography)


class SqlAlchemyPlaceRepository:
    """Place repository backed by SQLAlchemy (no commit: the caller owns the unit of work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_source_id(self, source: str, source_id: str) -> Place | None:
        row = await self._session.scalar(
            select(PlaceModel).where(PlaceModel.source == source, PlaceModel.source_id == source_id)
        )
        return place_from_model(row) if row is not None else None

    async def get_by_slug(self, slug: str) -> Place | None:
        row = await self._session.execute(
            select(PlaceModel, CategoryModel.slug)
            .outerjoin(CategoryModel, PlaceModel.category_id == CategoryModel.id)
            .where(PlaceModel.slug == slug)
        )
        found = row.first()
        if found is None:
            return None
        place = place_from_model(found[0])
        place.category_slug = found[1]
        return place

    async def add(self, place: Place) -> Place:
        model = PlaceModel(
            source=place.source,
            source_id=place.source_id,
            name=place.name,
            name_normalized=normalize_name(place.name),
            slug=place.slug,
            category_id=place.category_id,
            address_full=place.address_full,
            city=place.city,
            postal_code=place.postal_code,
            country_code=place.country_code,
            lat=place.lat,
            lng=place.lng,
            operating_status=place.operating_status,
            confidence=place.confidence,
            website=place.website,
            phone=place.phone,
            canonical_id=place.canonical_id,
        )
        self._session.add(model)
        await self._session.flush()
        return place_from_model(model)

    async def update(self, place: Place) -> Place:
        model = await self._session.get(PlaceModel, place.id)
        if model is None:
            raise DomainError(f"place '{place.slug}' is not persisted")
        model.name = place.name
        model.name_normalized = normalize_name(place.name)
        model.category_id = place.category_id
        model.address_full = place.address_full
        model.city = place.city
        model.postal_code = place.postal_code
        model.country_code = place.country_code
        model.lat = place.lat
        model.lng = place.lng
        model.operating_status = place.operating_status
        model.confidence = place.confidence
        model.website = place.website
        model.phone = place.phone
        model.canonical_id = place.canonical_id
        await self._session.flush()
        return place_from_model(model)

    async def list_near(
        self,
        lat: float,
        lng: float,
        radius: float,
        *,
        q: str | None = None,
        criterion_ids: Sequence[int] = (),
        family: HandicapFamily | None = None,
        limit: int = 50,
    ) -> list[PlaceHit]:
        point = _point(lat, lng)
        distance = func.ST_Distance(PlaceModel.location, point).label("distance")
        statement = (
            select(PlaceModel, CategoryModel.slug, distance)
            .outerjoin(CategoryModel, PlaceModel.category_id == CategoryModel.id)
            .where(
                PlaceModel.canonical_id.is_(None),
                PlaceModel.location.is_not(None),
                func.ST_DWithin(PlaceModel.location, point, radius),
            )
            .order_by(distance)
            .limit(limit)
        )
        if q:
            pattern = f"%{q.lower()}%"
            statement = statement.where(
                or_(
                    PlaceModel.name_normalized.ilike(pattern),
                    func.similarity(PlaceModel.name_normalized, q.lower()) > 0.2,
                )
            )
        if criterion_ids:
            # Existence is the MVP semantic: a value exists for the criterion requested.
            statement = statement.where(
                select(PlaceAccessibilityModel.place_id)
                .where(
                    PlaceAccessibilityModel.place_id == PlaceModel.id,
                    PlaceAccessibilityModel.criterion_id.in_(list(criterion_ids)),
                )
                .exists()
            )
        if family is not None:
            statement = statement.where(
                select(PlaceAccessibilityModel.place_id)
                .join(CriterionModel, CriterionModel.id == PlaceAccessibilityModel.criterion_id)
                .where(
                    PlaceAccessibilityModel.place_id == PlaceModel.id,
                    CriterionModel.handicap_families.contains([family]),
                )
                .exists()
            )
        rows = (await self._session.execute(statement)).all()
        hits = []
        for model, category_slug, metres in rows:
            place = place_from_model(model)
            place.category_slug = category_slug
            hits.append(PlaceHit(place=place, distance=float(metres)))
        return hits

    async def get_candidates(
        self,
        lat: float,
        lng: float,
        name: str,
        *,
        radius: float = DEFAULT_CANDIDATE_RADIUS,
        limit: int = 50,
    ) -> list[PlaceHit]:
        """Spatial blocking only: the caller scores the names (one scoring source)."""
        point = _point(lat, lng)
        distance = func.ST_Distance(PlaceModel.location, point).label("distance")
        rows = (
            await self._session.execute(
                select(PlaceModel, distance)
                .where(
                    PlaceModel.canonical_id.is_(None),
                    PlaceModel.location.is_not(None),
                    func.ST_DWithin(PlaceModel.location, point, radius),
                )
                .order_by(func.similarity(PlaceModel.name_normalized, name.lower()).desc())
                .limit(limit)
            )
        ).all()
        return [
            PlaceHit(place=place_from_model(model), distance=float(metres))
            for model, metres in rows
        ]

    async def list_accessibility(self, place_id: int) -> list[PlaceAccessibility]:
        rows = (
            await self._session.execute(
                select(PlaceAccessibilityModel, CriterionModel)
                .join(CriterionModel, CriterionModel.id == PlaceAccessibilityModel.criterion_id)
                .where(PlaceAccessibilityModel.place_id == place_id)
                .order_by(CriterionModel.position)
            )
        ).all()
        return [place_accessibility_from_models(value, criterion) for value, criterion in rows]


class SqlAlchemyPlaceAliasRepository:
    """Alias repository backed by SQLAlchemy (no commit: the caller owns the work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, place_id: int, name: str) -> None:
        self._session.add(PlaceAliasModel(place_id=place_id, name=name))
        await self._session.flush()

    async def list_for_place(self, place_id: int) -> list[str]:
        rows = (
            await self._session.scalars(
                select(PlaceAliasModel.name)
                .where(PlaceAliasModel.place_id == place_id)
                .order_by(PlaceAliasModel.name)
            )
        ).all()
        return list(rows)


class SqlAlchemyMergeLogRepository:
    """Merge-log repository backed by SQLAlchemy (no commit: the caller owns the work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, kept_id: int, merged_id: int, score: float, actor: str = "importer"
    ) -> None:
        self._session.add(
            PlaceMergeLogModel(kept_id=kept_id, merged_id=merged_id, score=score, actor=actor)
        )
        await self._session.flush()


class SqlAlchemyCategoryMappingRepository:
    """Resolve a source vocabulary term to a category (mapping table, then slug)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve_slug(self, slug: str) -> int | None:
        mapped = await self._session.scalar(
            select(CategoryMappingModel.category_id)
            .where(
                or_(
                    CategoryMappingModel.acceslibre_family == slug,
                    CategoryMappingModel.overture_category == slug,
                )
            )
            .limit(1)
        )
        if mapped is not None:
            return int(mapped)
        direct = await self._session.scalar(
            select(CategoryModel.id).where(CategoryModel.slug == slug)
        )
        return int(direct) if direct is not None else None
