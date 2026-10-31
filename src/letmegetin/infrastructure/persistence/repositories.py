"""SQLAlchemy implementations of the referential repository ports."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.accounts.entities import ApiKey, RefreshToken, User
from letmegetin.domain.places.dedup import normalize_name
from letmegetin.domain.places.entities import (
    HandicapFamily,
    Place,
    PlaceAccessibility,
    PlaceHit,
    PlacePhoto,
    Review,
)
from letmegetin.domain.places.repositories import DEFAULT_CANDIDATE_RADIUS
from letmegetin.domain.referential.entities import (
    AccessibilityFilter,
    Category,
    CategoryGrid,
    CategoryMapping,
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
    ApiKeyModel,
    CategoryCriterionModel,
    CategoryGridModel,
    CategoryMappingModel,
    CategoryModel,
    ContributionModel,
    CriterionModel,
    CriterionVocabularyModel,
    OtherInformationModel,
    PlaceAccessibilityModel,
    PlaceAliasModel,
    PlaceMergeLogModel,
    PlaceModel,
    PlacePhotoModel,
    ReferentialVersionModel,
    RefreshTokenModel,
    ReviewModel,
    UserModel,
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


class SqlAlchemyUserRepository:
    """Account repository backed by SQLAlchemy (no commit: the caller owns the work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        model = await self._session.scalar(select(UserModel).where(UserModel.email == email))
        return _user_from_model(model) if model is not None else None

    async def get_by_id(self, user_id: int) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _user_from_model(model) if model is not None else None

    async def add(self, user: User) -> User:
        model = UserModel(
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            display_name=user.display_name,
            email_verified=user.email_verified,
        )
        self._session.add(model)
        await self._session.flush()
        return _user_from_model(model)

    async def mark_email_verified(self, user_id: int) -> User | None:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            return None
        model.email_verified = True
        await self._session.flush()
        return _user_from_model(model)


def _user_from_model(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        role=model.role,
        display_name=model.display_name,
        email_verified=model.email_verified,
    )


class SqlAlchemyApiKeyRepository:
    """Partner API-key store backed by SQLAlchemy (no commit: the caller owns the work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, api_key: ApiKey) -> ApiKey:
        model = ApiKeyModel(
            label=api_key.label,
            key_hash=api_key.key_hash,
            rpm=api_key.rpm,
            active=api_key.active,
        )
        self._session.add(model)
        await self._session.flush()
        return _api_key_from_model(model)

    async def list_all(self) -> list[ApiKey]:
        rows = (await self._session.scalars(select(ApiKeyModel).order_by(ApiKeyModel.id))).all()
        return [_api_key_from_model(row) for row in rows]

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        model = await self._session.scalar(
            select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        )
        return _api_key_from_model(model) if model is not None else None

    async def revoke(self, key_id: int) -> ApiKey | None:
        model = await self._session.get(ApiKeyModel, key_id)
        if model is None:
            return None
        model.active = False
        await self._session.flush()
        return _api_key_from_model(model)


def _api_key_from_model(model: ApiKeyModel) -> ApiKey:
    return ApiKey(
        id=model.id,
        label=model.label,
        key_hash=model.key_hash,
        rpm=model.rpm,
        active=model.active,
    )


class SqlAlchemyRefreshTokenRepository:
    """Refresh-token store backed by SQLAlchemy (no commit: the caller owns the work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: int, token_hash: str, expires_at: datetime) -> None:
        self._session.add(
            RefreshTokenModel(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        )
        await self._session.flush()

    async def get(self, token_hash: str) -> RefreshToken | None:
        model = await self._session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        if model is None:
            return None
        return RefreshToken(
            user_id=model.user_id, expires_at=model.expires_at, revoked=model.revoked
        )

    async def revoke(self, token_hash: str) -> None:
        model = await self._session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        if model is not None:
            model.revoked = True
            await self._session.flush()


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

    async def upsert_accessibility(
        self, place_id: int, values: dict[str, dict[str, object]]
    ) -> None:
        if not values:
            return
        slugs = list(values)
        rows = (
            await self._session.execute(
                select(CriterionModel.id, CriterionModel.slug).where(CriterionModel.slug.in_(slugs))
            )
        ).all()
        if not rows:
            return
        statement = insert(PlaceAccessibilityModel).values(
            [
                {"place_id": place_id, "criterion_id": criterion_id, "value": values[slug]}
                for criterion_id, slug in rows
            ]
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[
                    PlaceAccessibilityModel.place_id,
                    PlaceAccessibilityModel.criterion_id,
                ],
                set_={"value": statement.excluded.value},
            )
        )

    async def upsert_photos(self, place_id: int, photos: Sequence[PlacePhoto]) -> None:
        if not photos:
            return
        statement = insert(PlacePhotoModel).values(
            [
                {
                    "place_id": place_id,
                    "url": photo.url,
                    "credit": photo.credit,
                    "license": photo.license,
                }
                for photo in photos
            ]
        )
        await self._session.execute(
            statement.on_conflict_do_nothing(constraint="place_photo_url_uc")
        )

    async def list_photos(self, place_id: int) -> list[PlacePhoto]:
        rows = (
            await self._session.scalars(
                select(PlacePhotoModel)
                .where(PlacePhotoModel.place_id == place_id)
                .order_by(PlacePhotoModel.id)
            )
        ).all()
        return [PlacePhoto(url=row.url, credit=row.credit, license=row.license) for row in rows]

    async def list_reviews(
        self, place_id: int, *, page: int, size: int
    ) -> tuple[list[Review], int]:
        conditions = (ReviewModel.place_id == place_id) & (ReviewModel.status == "published")
        total = await self._session.scalar(
            select(func.count()).select_from(ReviewModel).where(conditions)
        )
        rows = (
            await self._session.scalars(
                select(ReviewModel)
                .where(conditions)
                .order_by(ReviewModel.created.desc(), ReviewModel.id.desc())
                .offset((page - 1) * size)
                .limit(size)
            )
        ).all()
        return (
            [
                Review(
                    id=row.id,
                    rating=row.rating,
                    body=row.body,
                    author_name=row.author_name,
                    created=row.created,
                    status=row.status,
                )
                for row in rows
            ],
            int(total or 0),
        )

    async def review_stats(self, place_id: int) -> tuple[float | None, int]:
        average, count = (
            await self._session.execute(
                select(func.avg(ReviewModel.rating), func.count())
                .select_from(ReviewModel)
                .where(ReviewModel.place_id == place_id, ReviewModel.status == "published")
            )
        ).one()
        return (round(float(average), 1) if average is not None else None, int(count or 0))

    async def add_contribution(
        self, place_id: int, user_id: int, criterion_id: int, value: dict[str, object]
    ) -> None:
        self._session.add(
            ContributionModel(
                place_id=place_id, user_id=user_id, criterion_id=criterion_id, value=value
            )
        )
        await self._session.flush()

    async def add_review(
        self,
        place_id: int,
        user_id: int,
        rating: int,
        body: str,
        author_name: str | None,
    ) -> Review:
        model = ReviewModel(
            place_id=place_id,
            user_id=user_id,
            rating=rating,
            body=body,
            author_name=author_name,
            status="published",
        )
        self._session.add(model)
        await self._session.flush()
        return _review_from_model(model)

    async def set_review_status(self, review_id: int, status: str) -> Review | None:
        model = await self._session.get(ReviewModel, review_id)
        if model is None:
            return None
        model.status = status
        await self._session.flush()
        return _review_from_model(model)


def _review_from_model(model: ReviewModel) -> Review:
    return Review(
        id=model.id,
        rating=model.rating,
        body=model.body,
        author_name=model.author_name,
        created=model.created,
        status=model.status,
    )


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

    async def upsert(self, mapping: CategoryMapping) -> None:
        statement = insert(CategoryMappingModel).values(
            category_id=mapping.category_id,
            overture_category=mapping.overture_category,
            osm_tag=mapping.osm_tag,
            acceslibre_family=mapping.acceslibre_family,
            notes=mapping.notes,
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                constraint="category_mapping_category_uc",
                set_={
                    "overture_category": statement.excluded.overture_category,
                    "osm_tag": statement.excluded.osm_tag,
                    "acceslibre_family": statement.excluded.acceslibre_family,
                    "notes": statement.excluded.notes,
                    "updated": func.now(),
                },
            )
        )


class SqlAlchemyCategoryGridRepository:
    """Precomputed per-category grids and the global referential version."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def current_version(self) -> int:
        version = await self._session.scalar(
            select(ReferentialVersionModel.version).where(ReferentialVersionModel.id == 1)
        )
        return int(version or 1)

    async def bump_version(self) -> int:
        version = await self._session.scalar(
            update(ReferentialVersionModel)
            .where(ReferentialVersionModel.id == 1)
            .values(version=ReferentialVersionModel.version + 1)
            .returning(ReferentialVersionModel.version)
        )
        return int(version or 1)

    async def set_grid(self, category_id: int, version: int, tree: list[dict[str, object]]) -> None:
        statement = insert(CategoryGridModel).values(
            category_id=category_id, version=version, tree=tree
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[CategoryGridModel.category_id],
                set_={"version": version, "tree": tree, "updated": func.now()},
            )
        )

    async def get_for_slug(self, slug: str) -> CategoryGrid | None:
        row = (
            await self._session.execute(
                select(CategoryModel.slug, CategoryGridModel.version, CategoryGridModel.tree)
                .join(CategoryGridModel, CategoryGridModel.category_id == CategoryModel.id)
                .where(CategoryModel.slug == slug)
            )
        ).first()
        if row is None:
            return None
        return CategoryGrid(category_slug=row[0], version=int(row[1]), tree=row[2])
