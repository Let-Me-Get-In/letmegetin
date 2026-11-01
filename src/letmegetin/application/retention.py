"""Use case: purge operational data that has a retention limit (OPS-06)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from letmegetin.config import settings


@dataclass
class RetentionReport:
    idempotency_deleted: int
    refresh_deleted: int
    dry_run: bool


class RetentionRepository(Protocol):
    async def purge(
        self,
        *,
        idempotency_before: datetime,
        refresh_before: datetime,
        dry_run: bool,
    ) -> tuple[int, int]: ...


async def run_retention(
    repository: RetentionRepository,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
) -> RetentionReport:
    """Delete idempotency keys and session tokens past their retention window."""
    current = now or datetime.now(UTC).replace(tzinfo=None)
    idempotency_deleted, refresh_deleted = await repository.purge(
        idempotency_before=current - timedelta(hours=settings.retention_idempotency_hours),
        refresh_before=current - timedelta(days=settings.retention_refresh_days),
        dry_run=dry_run,
    )
    return RetentionReport(
        idempotency_deleted=idempotency_deleted,
        refresh_deleted=refresh_deleted,
        dry_run=dry_run,
    )
