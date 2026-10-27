"""Seed integration test: the vocabulary is loaded and the criteria tree is not polluted."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from letmegetin import seed as seed_module
from letmegetin.config import settings

# NullPool: each seed() call runs its own event loop via asyncio.run.
_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

_DATA: Path = settings.data_dir
_EXPECTED_VOCABULARY = len(json.loads((_DATA / "criteria.json").read_text(encoding="utf-8")))
_EXPECTED_CATEGORIES = len(json.loads((_DATA / "categories.json").read_text(encoding="utf-8")))
_GRID = json.loads((_DATA / "category_grids" / "category-1.json").read_text(encoding="utf-8"))
_EXPECTED_CRITERIA = sum(
    1
    + len(group.get("criteria", []))
    + sum(len(criterion.get("options", [])) for criterion in group.get("criteria", []))
    for group in _GRID
)

_COUNTS = (
    ("vocabulary", "criterion_vocabulary"),
    ("categories", "categories"),
    ("criteria", "criteria"),
    ("defaults", "criteria WHERE is_default"),
)


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            table = await session.scalar(text("SELECT to_regclass('criterion_vocabulary')"))
            return table is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


async def _count(statement: str) -> int:
    async with _TestSessionLocal() as session:
        return int(await session.scalar(text(statement)) or 0)


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if not asyncio.run(_database_ready()):
        pytest.skip("PostGIS database or criterion_vocabulary table unavailable")
    monkeypatch.setattr(seed_module, "SessionLocal", _TestSessionLocal)
    yield


def _counts() -> dict[str, int]:
    return {name: asyncio.run(_count(f"select count(*) from {source}")) for name, source in _COUNTS}


def test_seed_loads_vocabulary_without_polluting_criteria(db: None) -> None:
    asyncio.run(seed_module.seed())

    counts = _counts()
    assert counts["vocabulary"] == _EXPECTED_VOCABULARY
    assert counts["categories"] == _EXPECTED_CATEGORIES
    assert counts["criteria"] == _EXPECTED_CRITERIA
    assert counts["defaults"] > 0


def test_second_seed_changes_nothing(db: None) -> None:
    asyncio.run(seed_module.seed())
    first = _counts()

    asyncio.run(seed_module.seed())

    assert _counts() == first
