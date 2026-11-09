"""Sentry scrubbing and no-op behaviour."""

from __future__ import annotations

import pytest

from letmegetin.config import settings
from letmegetin.core.observability import before_send, init_sentry


def test_before_send_drops_the_request_and_redacts_emails() -> None:
    event = {
        "request": {"headers": {"authorization": "Bearer secret"}, "data": {"password": "x"}},
        "extra": {"contact": "alice@example.test"},
        "message": "failed for bob@example.test",
    }

    scrubbed = before_send(event, {})

    assert "request" not in scrubbed
    assert "alice@example.test" not in str(scrubbed)
    assert "bob@example.test" not in str(scrubbed)
    assert "[redacted-email]" in str(scrubbed)


def test_init_sentry_is_a_noop_without_a_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sentry_dsn", None)

    init_sentry()
