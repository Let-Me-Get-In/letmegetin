"""Admin CLI integration tests against the real PostGIS database.

Skips cleanly when the container or migration 0002 is absent, so `pytest` still
passes on a machine without Docker.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.config import settings
from letmegetin.infrastructure.persistence.models import CriterionVocabularyModel

# NullPool: each CLI invocation runs its own event loop via asyncio.run, and a pooled
# asyncpg connection cannot be reused from another loop.
_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

_SLUGS = ["cli-test-access", "cli-test-ramp", "cli-test-lift"]


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            table = await session.scalar(text("SELECT to_regclass('criterion_vocabulary')"))
            return table is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if not asyncio.run(_database_ready()):
        pytest.skip("PostGIS database or criterion_vocabulary table unavailable")
    monkeypatch.setattr(admin, "SessionLocal", _TestSessionLocal)
    yield
    asyncio.run(_delete_rows(_SLUGS))


async def _delete_rows(slugs: list[str]) -> None:
    async with _TestSessionLocal() as session:
        await session.execute(
            delete(CriterionVocabularyModel).where(CriterionVocabularyModel.slug.in_(slugs))
        )
        await session.commit()


async def _count_slugs(slugs: list[str]) -> int:
    async with _TestSessionLocal() as session:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(CriterionVocabularyModel)
                .where(CriterionVocabularyModel.slug.in_(slugs))
            )
            or 0
        )


def _write_entries(path: Path, entries: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_vocabulary_import_is_idempotent(db: None, tmp_path: Path) -> None:
    path = _write_entries(
        tmp_path / "criteria.json",
        [{"slug": slug, "label": {"fr": slug}, "description": {}} for slug in _SLUGS],
    )
    runner = CliRunner()

    first = runner.invoke(admin.app, ["vocabulary", "import", "--file", str(path)])
    assert first.exit_code == 0, first.output
    assert "created=3" in first.output
    assert asyncio.run(_count_slugs(_SLUGS)) == 3

    second = runner.invoke(admin.app, ["vocabulary", "import", "--file", str(path)])
    assert second.exit_code == 0, second.output
    assert "created=0" in second.output
    assert asyncio.run(_count_slugs(_SLUGS)) == 3


def test_vocabulary_import_rejects_entry_without_label(db: None, tmp_path: Path) -> None:
    path = _write_entries(
        tmp_path / "broken.json",
        [{"slug": "cli-test-broken", "label": {}, "description": {}}],
    )
    result = CliRunner().invoke(admin.app, ["vocabulary", "import", "--file", str(path)])

    assert result.exit_code == 1
    output = result.output
    assert "cli-test-broken" in output
    for sql_hint in ("SELECT", "INSERT", "sqlalchemy", "SQLAlchemy"):
        assert sql_hint not in output
