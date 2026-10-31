"""Keep tests deterministic: no shared Redis state and a fresh limiter per test."""

from __future__ import annotations

import pytest

from letmegetin.config import settings
from letmegetin.core.rate_limit import reset_memory_limits


@pytest.fixture(autouse=True)
def _deterministic_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "redis_url", None)
    reset_memory_limits()
    yield
    reset_memory_limits()
