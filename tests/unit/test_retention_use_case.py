"""Retention cutoffs and dry-run semantics."""

from __future__ import annotations

from datetime import datetime, timedelta

from letmegetin.application.retention import RetentionReport, run_retention


class _Repository:
    def __init__(self) -> None:
        self.idempotency_before: datetime | None = None
        self.refresh_before: datetime | None = None
        self.dry_run: bool | None = None

    async def purge(self, *, idempotency_before, refresh_before, dry_run):
        self.idempotency_before = idempotency_before
        self.refresh_before = refresh_before
        self.dry_run = dry_run
        return 3, 4


async def test_retention_uses_the_configured_windows() -> None:
    repository = _Repository()
    now = datetime(2026, 1, 2, 3, 4, 5)

    report = await run_retention(repository, now=now, dry_run=True)

    assert repository.idempotency_before == now - timedelta(hours=24)
    assert repository.refresh_before == now - timedelta(days=30)
    assert repository.dry_run is True
    assert report == RetentionReport(3, 4, True)
