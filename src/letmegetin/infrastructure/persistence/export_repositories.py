"""SQLAlchemy implementation of the export journal port (no commit: caller owns the work)."""

from __future__ import annotations

from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.domain.places.export import (
    ExportEntity,
    ExportEvent,
    ExportOp,
)
from letmegetin.infrastructure.persistence.models import ExportEventModel, PlaceModel


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
