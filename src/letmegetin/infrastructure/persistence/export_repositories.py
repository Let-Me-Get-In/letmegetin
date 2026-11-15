"""SQLAlchemy implementation of the export journal port (no commit: caller owns the work).

Also carries the bulk read an ODbL export streams: canonical places, remapped answers,
aliases and the exclusion counters. Every predicate is the SQL twin of the reviewed
licence matrix, never a branch here (LIC-05, D-13).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import cast

from sqlalchemy import ColumnElement, delete, exists, func, or_, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, aliased
from sqlalchemy.sql.selectable import CTE

from letmegetin.domain.places.export import (
    ExportEntity,
    ExportEvent,
    ExportOp,
)
from letmegetin.domain.places.export_plan import (
    AliasRow,
    AnswerRow,
    CategoryRow,
    CriterionRow,
    PlaceRow,
)
from letmegetin.infrastructure.persistence.models import (
    CategoryModel,
    CriterionModel,
    ExportEventModel,
    LicenceDestinationModel,
    PlaceAccessibilityModel,
    PlaceModel,
    ReferentialVersionModel,
)
from letmegetin.infrastructure.persistence.repositories import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyCriterionRepository,
)

# One server-side cursor feeds the writer: a page bounds the client-side buffer, never the
# full 635k-place / 1.7M-answer set (the plan's streaming requirement, W-DELTA-MEM).
_PAGE = 1000


def _event_from_model(model: ExportEventModel) -> ExportEvent:
    return ExportEvent(
        seq=model.seq,
        occurred_at=model.occurred_at,
        # The CHECK constraints keep the stored strings inside the Literal sets.
        entity=cast(ExportEntity, model.entity),
        entity_id=model.entity_id,
        op=cast(ExportOp, model.op),
        actor=model.actor,
        payload=model.payload,
    )


def _licence_allows(
    licence: ColumnElement[str | None] | InstrumentedAttribute[str | None], destination: str
) -> ColumnElement[bool]:
    """The SQL twin of ``can_redistribute`` for one row's own licence column (D-13).

    A NULL or unknown licence matches nothing — fail-closed, like the domain predicate.
    ``destination`` is a bound parameter, never interpolated (T-12-04).
    """
    return exists(
        select(1).where(
            LicenceDestinationModel.licence_slug == licence,
            LicenceDestinationModel.destination == destination,
            LicenceDestinationModel.allowed.is_(True),
        )
    )


def _answer_may_leave(destination: str) -> ColumnElement[bool]:
    """The answer's OWN licence decides (D-03), not its place's."""
    return _licence_allows(PlaceAccessibilityModel.source_license, destination)


def _place_changed_after(seq: int) -> ColumnElement[bool]:
    return exists(
        select(1).where(
            ExportEventModel.entity == "place",
            ExportEventModel.entity_id == PlaceModel.id,
            ExportEventModel.seq > seq,
        )
    )


def _ranked_answers(destination: str) -> CTE:
    """One winner per (effective canonical place, criterion) over the FULL population (W4).

    Ranking happens before any window filter: a delta picks the same winner the snapshot
    did, and a merged place's answer competes under its canonical id (D-04).
    """
    canonical = aliased(PlaceModel)
    effective = func.coalesce(PlaceModel.canonical_id, PlaceModel.id)
    return (
        select(
            effective.label("canonical_id"),
            CriterionModel.slug.label("criterion_slug"),
            PlaceAccessibilityModel.criterion_id.label("criterion_id"),
            PlaceAccessibilityModel.place_id.label("source_place_id"),
            PlaceAccessibilityModel.value,
            PlaceAccessibilityModel.source,
            PlaceAccessibilityModel.source_license,
            PlaceAccessibilityModel.observed_at,
            PlaceAccessibilityModel.recorded_at,
            func.row_number()
            .over(
                partition_by=(effective, PlaceAccessibilityModel.criterion_id),
                order_by=(
                    (PlaceAccessibilityModel.place_id == effective).desc(),
                    PlaceAccessibilityModel.recorded_at.desc(),
                    PlaceAccessibilityModel.place_id.desc(),
                    PlaceAccessibilityModel.criterion_id.desc(),
                ),
            )
            .label("rn"),
        )
        .select_from(PlaceAccessibilityModel)
        .join(PlaceModel, PlaceModel.id == PlaceAccessibilityModel.place_id)
        .join(canonical, canonical.id == effective)
        .join(CriterionModel, CriterionModel.id == PlaceAccessibilityModel.criterion_id)
        .where(_licence_allows(canonical.source_license, destination))
        .where(_answer_may_leave(destination))
    ).cte("ranked_answers")


def _answer_changed_in(ranked: CTE, window: tuple[int, int]) -> ColumnElement[bool]:
    """Whether the winner's inputs moved in ``window`` — applied AFTER ranking (B7, W7).

    The answer event carries the PLACE id in ``entity_id``, so the join is on the payload's
    ``criterion_slug`` and on the event place's canonical id, never on ``entity_id`` alone.
    """
    low, high = window
    event_canonical = func.coalesce(
        select(PlaceModel.canonical_id)
        .where(PlaceModel.id == ExportEventModel.entity_id)
        .scalar_subquery(),
        ExportEventModel.entity_id,
    )
    return or_(
        exists(
            select(1).where(
                ExportEventModel.entity == "place_accessibility",
                ExportEventModel.seq > low,
                ExportEventModel.seq <= high,
                ExportEventModel.payload["criterion_slug"].astext == ranked.c.criterion_slug,
                event_canonical == ranked.c.canonical_id,
            )
        ),
        exists(
            select(1).where(
                ExportEventModel.entity == "place",
                ExportEventModel.op == "merge",
                ExportEventModel.seq > low,
                ExportEventModel.seq <= high,
                or_(
                    ExportEventModel.entity_id == ranked.c.canonical_id,
                    ExportEventModel.entity_id.in_(
                        select(PlaceModel.id)
                        .where(PlaceModel.canonical_id == ranked.c.canonical_id)
                        .correlate(ranked)
                    ),
                ),
            )
        ),
    )


class SqlAlchemyExportEventRepository:
    """Append-only journal backed by SQLAlchemy (no commit: the caller owns the work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        entity: ExportEntity,
        entity_id: int,
        op: ExportOp,
        actor: str,
        payload: dict[str, object],
    ) -> None:
        self._session.add(
            ExportEventModel(
                entity=entity, entity_id=entity_id, op=op, actor=actor, payload=payload
            )
        )
        await self._session.flush()

    async def list_events(self, place_id: int) -> list[ExportEvent]:
        rows = (
            await self._session.scalars(
                select(ExportEventModel)
                .where(ExportEventModel.entity_id == place_id)
                .order_by(ExportEventModel.seq)
            )
        ).all()
        return [_event_from_model(row) for row in rows]

    async def list_events_by_slug(self, slug: str) -> list[ExportEvent]:
        rows = (
            await self._session.scalars(
                select(ExportEventModel)
                .join(PlaceModel, PlaceModel.id == ExportEventModel.entity_id)
                .where(PlaceModel.slug == slug)
                .order_by(ExportEventModel.seq)
            )
        ).all()
        return [_event_from_model(row) for row in rows]

    async def safe_seq(self) -> int:
        """Highest seq whose inserting transaction has ended (D-10); 0 when empty.

        A SELECT, so calling it first inside a REPEATABLE READ transaction pins the snapshot
        the delta reads: the boundary and the streamed rows then agree by construction.
        """
        boundary = await self._session.scalar(
            select(func.coalesce(func.max(ExportEventModel.seq), 0)).where(
                ExportEventModel.xid < func.pg_snapshot_xmin(func.pg_current_snapshot())
            )
        )
        return int(boundary or 0)

    async def seq_at_or_before(self, moment: datetime) -> int:
        """The ``--since <date>`` boundary, read inside the export's snapshot (D-10)."""
        boundary = await self._session.scalar(
            select(func.coalesce(func.max(ExportEventModel.seq), 0)).where(
                ExportEventModel.occurred_at <= moment
            )
        )
        return int(boundary or 0)

    async def delete_up_to(self, seq: int) -> int:
        """Retention (D-15): prune the journal up to a COMPLETED snapshot boundary."""
        result = await self._session.execute(
            delete(ExportEventModel).where(ExportEventModel.seq <= seq)
        )
        return int(cast(CursorResult[tuple[object, ...]], result).rowcount or 0)


class SqlAlchemyExportRepository:
    """Bulk read for the ODbL export (no commit: the caller owns the work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def begin_repeatable_read(self) -> None:
        """Pin one snapshot before the first statement, so boundary and rows agree (B5)."""
        await self._session.connection(execution_options={"isolation_level": "REPEATABLE READ"})

    async def referential_version(self) -> int:
        version = await self._session.scalar(
            select(ReferentialVersionModel.version).where(ReferentialVersionModel.id == 1)
        )
        return int(version or 1)

    async def licence_rules_count(self) -> int:
        """Rows in the reviewed matrix; zero means `admin licences sync` never ran (D-15)."""
        count = await self._session.scalar(
            select(func.count()).select_from(LicenceDestinationModel)
        )
        return int(count or 0)

    async def stream_canonical_places(
        self, destination: str, since_seq: int | None = None
    ) -> AsyncIterator[PlaceRow]:
        """Every canonical place the matrix lets leave, in id order (D-04)."""
        statement = (
            select(
                PlaceModel.id,
                PlaceModel.source_id,
                PlaceModel.slug,
                PlaceModel.name,
                CategoryModel.slug.label("category_slug"),
                PlaceModel.source_category,
                PlaceModel.address_full,
                PlaceModel.city,
                PlaceModel.postal_code,
                PlaceModel.country_code,
                PlaceModel.lat,
                PlaceModel.lng,
                PlaceModel.operating_status,
                PlaceModel.website,
                PlaceModel.phone,
                PlaceModel.source,
                PlaceModel.source_license,
                PlaceModel.source_url,
                PlaceModel.observed_at,
                PlaceModel.retrieved_at,
                PlaceModel.erp_slug,
            )
            .outerjoin(CategoryModel, CategoryModel.id == PlaceModel.category_id)
            .where(PlaceModel.canonical_id.is_(None))
            .where(_licence_allows(PlaceModel.source_license, destination))
            .order_by(PlaceModel.id)
        )
        if since_seq is not None:
            statement = statement.where(_place_changed_after(since_seq))
        result = await self._session.stream(statement.execution_options(yield_per=_PAGE))
        async for row in result:
            yield PlaceRow(
                place_id=row.id,
                origin_id=row.source_id,
                slug=row.slug,
                name=row.name,
                category_slug=row.category_slug,
                source_category=row.source_category,
                address_full=row.address_full,
                city=row.city,
                postal_code=row.postal_code,
                country_code=row.country_code,
                lat=row.lat,
                lng=row.lng,
                operating_status=row.operating_status,
                website=row.website,
                phone=row.phone,
                source=row.source,
                source_license=row.source_license,
                source_url=row.source_url,
                # Source-first date (D-06): the source's claim, else our retrieval.
                date=row.observed_at or row.retrieved_at,
                erp_slug=row.erp_slug,
            )

    async def stream_answers(
        self, destination: str, window: tuple[int, int] | None = None
    ) -> AsyncIterator[AnswerRow]:
        """The winning answer per (canonical place, criterion), merged places remapped (D-04)."""
        ranked = _ranked_answers(destination)
        statement = (
            select(
                ranked.c.canonical_id,
                ranked.c.criterion_slug,
                ranked.c.value,
                ranked.c.source,
                ranked.c.source_license,
                ranked.c.observed_at,
                ranked.c.recorded_at,
            )
            .where(ranked.c.rn == 1)
            .order_by(ranked.c.canonical_id, ranked.c.criterion_id)
        )
        if window is not None:
            statement = statement.where(_answer_changed_in(ranked, window))
        result = await self._session.stream(statement.execution_options(yield_per=_PAGE))
        async for row in result:
            yield AnswerRow(
                place_id=row.canonical_id,
                criterion_slug=row.criterion_slug,
                value=row.value,
                source=row.source,
                source_license=row.source_license,
                # An answer has no retrieved_at: observed_at else recorded_at (I2).
                date=row.observed_at or row.recorded_at,
            )

    async def stream_aliases(self, since_seq: int | None = None) -> AsyncIterator[AliasRow]:
        """Every merged place and its canonical id — the incremental tombstone stream (D-04).

        Each side also carries its identifier candidates, so the partner projection can key the
        pair on AccesLibre's identifiers without a second lookup; the ODbL CSV reads only the ids.
        """
        canonical = aliased(PlaceModel)
        statement = (
            select(
                PlaceModel.id,
                PlaceModel.canonical_id,
                PlaceModel.erp_slug,
                PlaceModel.source_id,
                canonical.erp_slug.label("canonical_erp_slug"),
                canonical.source_id.label("canonical_origin_id"),
            )
            .join(canonical, canonical.id == PlaceModel.canonical_id)
            .where(PlaceModel.canonical_id.isnot(None))
            .order_by(PlaceModel.id)
        )
        if since_seq is not None:
            statement = statement.where(
                exists(
                    select(1).where(
                        ExportEventModel.entity == "place",
                        ExportEventModel.op == "merge",
                        ExportEventModel.entity_id == PlaceModel.id,
                        ExportEventModel.seq > since_seq,
                    )
                )
            )
        result = await self._session.stream(statement)
        async for row in result:
            if row.canonical_id is None:  # narrowed for the type checker
                continue
            yield AliasRow(
                alias_id=row.id,
                canonical_id=row.canonical_id,
                alias_erp_slug=row.erp_slug,
                alias_origin_id=row.source_id,
                canonical_erp_slug=row.canonical_erp_slug,
                canonical_origin_id=row.canonical_origin_id,
            )

    async def list_categories(self) -> list[CategoryRow]:
        categories = await SqlAlchemyCategoryRepository(self._session).list_all()
        slugs = {category.id: category.slug for category in categories}
        return [
            CategoryRow(
                category_id=category.id,
                slug=category.slug,
                parent_id=category.parent_id,
                parent_slug=slugs.get(category.parent_id) if category.parent_id else None,
                name=category.name,
                label=dict(category.label),
            )
            for category in categories
        ]

    async def list_criteria(self) -> list[CriterionRow]:
        criteria = await SqlAlchemyCriterionRepository(self._session).list_all()
        slugs = {criterion.id: criterion.slug for criterion in criteria}
        return [
            CriterionRow(
                criterion_id=criterion.id,
                slug=criterion.slug,
                parent_id=criterion.parent_id,
                parent_slug=slugs.get(criterion.parent_id) if criterion.parent_id else None,
                type=criterion.type,
                position=criterion.position,
                handicap_families=list(criterion.handicap_families),
                label=dict(criterion.label),
                en17210_ref=criterion.en17210_ref,
            )
            for criterion in criteria
        ]

    async def place_exclusion_counts(self, destination: str) -> list[tuple[str, str | None, int]]:
        """Canonical places the matrix withholds — merged places are not counted twice (D-14)."""
        statement = (
            select(PlaceModel.source, PlaceModel.source_license, func.count(PlaceModel.id))
            .where(PlaceModel.canonical_id.is_(None))
            .where(~_licence_allows(PlaceModel.source_license, destination))
            .group_by(PlaceModel.source, PlaceModel.source_license)
            .order_by(PlaceModel.source, PlaceModel.source_license)
        )
        found = (await self._session.execute(statement)).all()
        return [(str(source), licence, int(count)) for source, licence, count in found]

    async def answer_exclusion_counts(self, destination: str) -> list[tuple[str, str | None, int]]:
        """Withheld answers AND ranking losers, per (source, licence) (D-03, D-04)."""
        canonical = aliased(PlaceModel)
        effective = func.coalesce(PlaceModel.canonical_id, PlaceModel.id)
        withheld = (
            select(
                PlaceAccessibilityModel.source,
                PlaceAccessibilityModel.source_license,
                func.count(),
            )
            .select_from(PlaceAccessibilityModel)
            .join(PlaceModel, PlaceModel.id == PlaceAccessibilityModel.place_id)
            .join(canonical, canonical.id == effective)
            .where(_licence_allows(canonical.source_license, destination))
            .where(~_answer_may_leave(destination))
            .group_by(PlaceAccessibilityModel.source, PlaceAccessibilityModel.source_license)
        )
        ranked = _ranked_answers(destination)
        losers = (
            select(ranked.c.source, ranked.c.source_license, func.count())
            .where(ranked.c.rn > 1)
            .group_by(ranked.c.source, ranked.c.source_license)
        )
        totals: dict[tuple[str, str | None], int] = {}
        for statement in (withheld, losers):
            for source, licence, count in (await self._session.execute(statement)).all():
                key = (str(source), licence)
                totals[key] = totals.get(key, 0) + int(count)
        return [
            (source, licence, count)
            for (source, licence), count in sorted(
                totals.items(), key=lambda item: (item[0][0], item[0][1] or "")
            )
        ]

    async def place_withheld_answer_counts(
        self, destination: str
    ) -> list[tuple[str, str | None, int]]:
        """Answers whose canonical place never leaves at all, counted apart (W3)."""
        canonical = aliased(PlaceModel)
        effective = func.coalesce(PlaceModel.canonical_id, PlaceModel.id)
        statement = (
            select(
                PlaceAccessibilityModel.source,
                PlaceAccessibilityModel.source_license,
                func.count(),
            )
            .select_from(PlaceAccessibilityModel)
            .join(PlaceModel, PlaceModel.id == PlaceAccessibilityModel.place_id)
            .join(canonical, canonical.id == effective)
            .where(~_licence_allows(canonical.source_license, destination))
            .group_by(PlaceAccessibilityModel.source, PlaceAccessibilityModel.source_license)
            .order_by(PlaceAccessibilityModel.source, PlaceAccessibilityModel.source_license)
        )
        found = (await self._session.execute(statement)).all()
        return [(str(source), licence, int(count)) for source, licence, count in found]
