"""The Typer CLI wrapper reports success and domain errors (no database)."""

from __future__ import annotations

from typing import Any

import pytest
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.core.exceptions import CategoryAlreadyExists
from letmegetin.domain.referential.entities import Category


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self) -> _FakeSessionFactory:
        return self

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, *exc: object) -> bool:
        return False


def test_cli_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()

    async def fake_add(repository: Any, slug: str, name: str, label: Any) -> Category:
        return Category(id=1, slug=slug, name=name, label=label)

    async def fake_grids(*args: Any, **kwargs: Any) -> int:
        return 1

    monkeypatch.setattr(admin, "add_category", fake_add)
    monkeypatch.setattr(admin, "rebuild_category_grids", fake_grids)
    monkeypatch.setattr(admin, "SessionLocal", _FakeSessionFactory(session))

    result = CliRunner().invoke(admin.app, ["category", "add", "garden", "--name", "Garden"])

    assert result.exit_code == 0, result.output
    assert "garden" in result.output
    assert session.committed


def test_cli_reports_domain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_add(repository: Any, slug: str, name: str, label: Any) -> Category:
        raise CategoryAlreadyExists(slug)

    monkeypatch.setattr(admin, "add_category", fake_add)
    monkeypatch.setattr(admin, "SessionLocal", _FakeSessionFactory(_FakeSession()))

    result = CliRunner().invoke(admin.app, ["category", "add", "garden", "--name", "Garden"])

    assert result.exit_code == 1
    assert "already exists" in result.output
