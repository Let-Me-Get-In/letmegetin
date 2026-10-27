"""Acceslibre import integration test against the real PostGIS database.

Skips cleanly when the container or migration 0003 is absent.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.config import settings

# NullPool: each CLI invocation runs its own event loop via asyncio.run.
_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

_FIXTURE = (
    "id;nom;adresse;commune;code_postal;latitude;longitude;categorie;site_internet;"
    "telephone\n"
    "test-1;Médiathèque Test Alpha;1 rue des Tests;Testville;99001;45.1000;5.1000;"
    "bibliotheque;https://example.test;+33400000000\n"
    "test-2;Mediatheque Test Alpha;1 rue des Tests;Testville;99001;45.1000;5.1000;"
    "bibliotheque;;\n"
    "test-3;Mediatheque Test Alpha Annexe;1 rue des Tests;Testville;99001;45.1000;5.1000;"
    "bibliotheque;;\n"
)


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            table = await session.scalar(text("SELECT to_regclass('place')"))
            return table is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _cleanup() -> None:
    async with _TestSessionLocal() as session:
        await session.execute(
            text("DELETE FROM place WHERE source = 'acceslibre' AND source_id LIKE 'test-%'")
        )
        await session.commit()


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if not asyncio.run(_database_ready()):
        pytest.skip("PostGIS database or place table unavailable")
    asyncio.run(_cleanup())
    monkeypatch.setattr(admin, "SessionLocal", _TestSessionLocal)
    yield
    asyncio.run(_cleanup())


async def _query(statement: str) -> list[tuple]:
    async with _TestSessionLocal() as session:
        return list((await session.execute(text(statement))).all())


def _places(statement: str) -> list[tuple]:
    return asyncio.run(_query(statement))


def _import(path: Path) -> str:
    result = CliRunner().invoke(admin.app, ["import", "acceslibre", "--file", str(path)])
    assert result.exit_code == 0, result.output
    return result.output


def test_acceslibre_import_is_idempotent_and_deduplicated(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_FIXTURE, encoding="utf-8")

    first = _import(path)
    assert "created=3" in first
    assert "linked=1" in first
    assert "review=1" in first

    second = _import(path)
    assert "created=0" in second
    assert "skipped=3" in second

    rows = _places(
        "SELECT source_id, canonical_id, operating_status FROM place "
        "WHERE source = 'acceslibre' AND source_id LIKE 'test-%' ORDER BY source_id"
    )
    assert [row[0] for row in rows] == ["test-1", "test-2", "test-3"]

    canonical, linked, review = rows[0][1], rows[1][1], rows[2]
    assert canonical is None
    assert linked is not None
    assert review[1] is None
    assert review[2] == "duplicate_review"


def test_acceslibre_import_logs_the_merge_and_keeps_the_alias(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_FIXTURE, encoding="utf-8")
    _import(path)

    merges = _places(
        "SELECT score FROM place_merge_log WHERE actor = 'acceslibre' "
        "AND kept_id IN (SELECT id FROM place WHERE source_id LIKE 'test-%')"
    )
    assert len(merges) == 1
    assert merges[0][0] > 0.9

    aliases = _places(
        "SELECT name FROM place_alias WHERE place_id = "
        "(SELECT id FROM place WHERE source_id = 'test-1')"
    )
    assert [row[0] for row in aliases] == ["Mediatheque Test Alpha"]
