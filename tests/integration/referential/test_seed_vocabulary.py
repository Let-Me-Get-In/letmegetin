"""Seed integration test: the vocabulary is loaded and the criteria tree is not polluted."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text

from letmegetin import seed as seed_module
from letmegetin.config import settings
from tests.db import SessionLocal, require_database

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
    ("criteria_without_families", "criteria WHERE handicap_families = '{}'"),
    ("filters_without_families", "accessibility_filters WHERE handicap_families = '{}'"),
)


async def _count(statement: str) -> int:
    async with SessionLocal() as session:
        return int(await session.scalar(text(statement)) or 0)


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    require_database("criterion_vocabulary")
    monkeypatch.setattr(seed_module, "SessionLocal", SessionLocal)
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
    assert counts["criteria_without_families"] == 0
    assert counts["filters_without_families"] == 0


def test_second_seed_changes_nothing(db: None) -> None:
    asyncio.run(seed_module.seed())
    first = _counts()

    asyncio.run(seed_module.seed())

    assert _counts() == first
