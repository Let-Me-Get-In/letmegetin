"""Production settings guard."""

from __future__ import annotations

import pytest

from letmegetin.config import settings
from letmegetin.main import DEFAULT_JWT_SECRET, _validate_settings


def test_production_refuses_the_development_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "jwt_secret", DEFAULT_JWT_SECRET)

    with pytest.raises(RuntimeError):
        _validate_settings()


def test_production_accepts_a_real_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "jwt_secret", "a-real-secret")

    _validate_settings()
