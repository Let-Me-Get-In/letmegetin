"""Category-grid rebuild use case driven through fake repositories (no database)."""

from __future__ import annotations

from typing import Any

from letmegetin.application.referential.admin import rebuild_category_grids
from tests.unit.application.referential.fakes import FakeCategoryGridRepository


async def test_rebuild_category_grids_bumps_the_version_and_stores_every_tree(
    stores: tuple[Any, ...],
) -> None:
    categories, criteria, _, _ = stores
    grids = FakeCategoryGridRepository()

    version = await rebuild_category_grids(categories, criteria, grids)

    assert version == 2
    assert grids.grids[10][0] == 2
    root = grids.grids[10][1][0]
    assert root["slug"] == "entree"
    assert root["children"][0]["slug"] == "entree-acces"
