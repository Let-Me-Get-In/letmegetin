"""Keep tests deterministic: an isolated database, no shared Redis state, a fresh limiter."""

from __future__ import annotations

import os

# Must run before anything imports `letmegetin.core.db`: the engine is built from
# `settings.database_url` at import time. Without this the suite shares the
# development database, so a real import (634 931 places) breaks every test that
# assumes it owns the `place` table.
os.environ.setdefault(
    "LETMEGETIN_DATABASE_URL",
    "postgresql+asyncpg://letmegetin:letmegetin@localhost:55433/letmegetin_test",
)

import pytest  # noqa: E402

from letmegetin.config import settings
from letmegetin.core.rate_limit import reset_memory_limits


@pytest.fixture(autouse=True)
def _deterministic_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "redis_url", None)
    reset_memory_limits()
    yield
    reset_memory_limits()
