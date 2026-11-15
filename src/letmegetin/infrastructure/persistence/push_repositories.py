"""SQLAlchemy implementation of the outbound push port (no commit: the caller owns the work).

Two responsibilities, both D-12: stream the answers we own for one destination, and append the
journal row for every decision. The licence gate lives in the stream predicate — a row whose
licence withholds it from the destination never reaches the use case at all (fail-closed).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.acceslibre_push import AcceslibrePushWrite, OwnedAnswer
from letmegetin.infrastructure.persistence.export_repositories import _PAGE, _licence_allows
from letmegetin.infrastructure.persistence.models import (
    AccesLibrePushWriteModel,
    CriterionModel,
    PlaceAccessibilityModel,
    PlaceModel,
)

# The only source a push may carry: an answer we own (D-11). Never an acceslibre import.
_DESTINATION_SOURCE = "user"


def _owned_answers(destination: str) -> Select[tuple[object, ...]]:
    """The winning user answer per (canonical place, criterion) the matrix lets leave.

    Ranking happens before the licence gate is applied to the row's own licence, and merged
    places compete under their canonical id — the same shape as the export's answer stream.
    """
    canonical = aliased(PlaceModel)
    effective = func.coalesce(PlaceModel.canonical_id, PlaceModel.id)
    ranked = (
        select(
            effective.label("canonical_id"),
            PlaceAccessibilityModel.criterion_id.label("criterion_id"),
            CriterionModel.slug.label("criterion_slug"),
            PlaceAccessibilityModel.value,
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
                ),
            )
            .label("rn"),
        )
        .select_from(PlaceAccessibilityModel)
        .join(PlaceModel, PlaceModel.id == PlaceAccessibilityModel.place_id)
        .join(canonical, canonical.id == effective)
        .join(CriterionModel, CriterionModel.id == PlaceAccessibilityModel.criterion_id)
        .where(PlaceAccessibilityModel.source == _DESTINATION_SOURCE)
        .where(_licence_allows(PlaceAccessibilityModel.source_license, destination))
    ).cte("owned_answers")

    return (
        select(
            ranked.c.canonical_id,
            ranked.c.criterion_slug,
            ranked.c.value,
            ranked.c.source_license,
            ranked.c.observed_at,
            ranked.c.recorded_at,
            PlaceModel.slug.label("place_slug"),
            PlaceModel.erp_slug,
            PlaceModel.source_id,
        )
        .join(PlaceModel, PlaceModel.id == ranked.c.canonical_id)
        .where(ranked.c.rn == 1)
        .order_by(ranked.c.canonical_id, ranked.c.criterion_id)
    )


class SqlAlchemyPushRepository:
    """The domain port's two methods, backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._criteria: dict[str, int] = {}

    async def stream_owned_answers(self, destination: str) -> AsyncIterator[OwnedAnswer]:
        result = await self._session.stream(
            _owned_answers(destination).execution_options(yield_per=_PAGE)
        )
        async for row in result:
            yield OwnedAnswer(
                place_id=row.canonical_id,
                place_slug=row.place_slug,
                criterion_slug=row.criterion_slug,
                value=row.value,
                observed_at=row.observed_at,
                recorded_at=row.recorded_at,
                origin_id=row.source_id,
                erp_slug=row.erp_slug,
                source_license=row.source_license,
            )

    async def append(self, journal: AcceslibrePushWrite) -> None:
        self._session.add(
            AccesLibrePushWriteModel(
                place_id=journal.place_id,
                criterion_id=await self._criterion_id(journal.criterion_slug),
                value=dict(journal.value),
                source=journal.source,
                source_license=journal.source_license,
                decision=journal.decision,
                reason=journal.reason,
                actor=journal.actor,
            )
        )
        await self._session.flush()

    async def _criterion_id(self, slug: str) -> int:
        """The FK target, cached for the run: a streamed criterion always exists in the DB."""
        found = self._criteria.get(slug)
        if found is None:
            found = await self._session.scalar(
                select(CriterionModel.id).where(CriterionModel.slug == slug)
            )
            if found is None:
                raise DomainError(f"acceslibre push journal: unknown criterion {slug!r}")
            self._criteria[slug] = found
        return found
