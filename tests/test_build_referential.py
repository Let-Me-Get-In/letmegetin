"""Tests for the seed generator (stdlib parser, no database)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.build_referential import (
    build_categories,
    build_criteria,
    build_filters,
    build_th,
    extract_category_one_grid,
)

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "referential" / "raw"

pytestmark = pytest.mark.skipif(
    not (RAW_DIR / "category.csv").exists(),
    reason="private raw referential sources are not committed",
)


def test_categories_have_slug_and_labels() -> None:
    categories = build_categories()
    assert len(categories) >= 150
    assert all(category["slug"] and category["label"] for category in categories)


def test_criteria_vocabulary_is_deduplicated() -> None:
    criteria = build_criteria()
    assert len(criteria) >= 150
    slugs = [criterion["slug"] for criterion in criteria]
    assert len(slugs) == len(set(slugs))
    assert any(criterion["label"].get("fr") for criterion in criteria)


def test_filters() -> None:
    assert len(build_filters()) >= 50


def test_other_information() -> None:
    assert len(build_th()) >= 15


def test_category_one_grid_structure() -> None:
    grid = extract_category_one_grid()
    assert len(grid) == 4
    assert sum(len(group["criteria"]) for group in grid) == 19
    assert grid[0]["name"] == "ENTRÉE"
