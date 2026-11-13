"""Fixtures shared by the functional suite (real entry points, real PostGIS)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin import admin
from letmegetin import seed as seed_module
from letmegetin.core.db import get_session
from letmegetin.main import app
from tests.db import SessionLocal, require_database, seed_source_licences


@pytest.fixture(autouse=True)
def reviewed_source_licences() -> None:
    """Every write resolves its licence from reviewed data; the test DB must hold it (LIC-05)."""
    require_database("source_licence")
    seed_source_licences()


@pytest.fixture
def test_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the CLI and the seed loader at the NullPool test factory."""
    monkeypatch.setattr(admin, "SessionLocal", SessionLocal)
    monkeypatch.setattr(seed_module, "SessionLocal", SessionLocal)


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    """Default data fixture; a module overrides it to seed and clean its rows."""
    require_database()
    yield


@pytest.fixture
def client(db: None) -> Iterator[TestClient]:
    async def override() -> AsyncIterator[AsyncSession]:
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
