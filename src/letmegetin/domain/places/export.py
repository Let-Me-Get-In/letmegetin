"""Export journal: the append-only event, its port, and the read-time diff (D-07…D-13)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Protocol
from uuid import UUID

from letmegetin.core.exceptions import DomainError

ExportEntity = Literal["place", "place_accessibility"]
ExportOp = Literal["insert", "update", "merge"]


@dataclass(frozen=True, slots=True)
class ExportEvent:
    """One appended journal row; ``xid`` stays a persistence detail, never read here."""

    seq: int
    occurred_at: datetime
    entity: ExportEntity
    entity_id: int
    op: ExportOp
    actor: str
    payload: dict[str, object]


class ExportEventRepository(Protocol):
    """The append-only journal and its MVCC boundary (D-10)."""

    async def append(
        self,
        entity: ExportEntity,
        entity_id: int,
        op: ExportOp,
        actor: str,
        payload: dict[str, object],
    ) -> None: ...

    async def list_events(self, place_id: int) -> list[ExportEvent]:
        """Every event of a place id, in ``seq`` order."""
        ...

    async def list_events_by_slug(self, slug: str) -> list[ExportEvent]:
        """The same read resolved by slug; an unknown slug is empty, never an error."""
        ...

    async def safe_seq(self) -> int:
        """Highest ``seq`` whose inserting transaction has ended; 0 when empty."""
        ...

    async def seq_at_or_before(self, moment: datetime) -> int:
        """The last ``seq`` that occurred at or before ``moment``; 0 when none did."""
        ...

    async def delete_up_to(self, seq: int) -> int:
        """Retention: delete the events at or below a completed snapshot boundary."""
        ...


def describe_changes(before: dict[str, object], after: dict[str, object]) -> dict[str, object]:
    """Top-level keys whose value differs, mapped to their new value (D-13, read time)."""
    return {
        key: after.get(key)
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        # Fail-closed: JSONB cannot store NaN/Infinity, and a silent journal gap is worse
        # than the write it aborts (D-08).
        if not math.isfinite(value):
            raise DomainError(f"export payload carries a non-finite number: {value!r}")
        return value
    if isinstance(value, datetime):
        moment = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return moment.astimezone(UTC).isoformat()
    if isinstance(value, (UUID, Enum)):
        return str(value)
    return value


def _jsonable(model_row: Mapping[str, object]) -> dict[str, object]:
    """Coerce a row's values into something JSONB stores; raises on a non-finite number."""
    return {key: _json_value(value) for key, value in model_row.items()}
