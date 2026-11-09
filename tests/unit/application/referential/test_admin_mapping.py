"""Source-mapping use cases driven through fake repositories (no database)."""

from __future__ import annotations

from typing import Any

import pytest

from letmegetin.application.referential.admin import map_category
from letmegetin.core.exceptions import CategoryNotFound
from tests.unit.application.referential.fakes import FakeMappingAdminRepository


async def test_map_category_upserts_the_source_vocabularies(stores: tuple[Any, ...]) -> None:
    categories, _, _, _ = stores
    mapping = FakeMappingAdminRepository()

    category = await map_category(
        mapping,
        categories,
        "restaurant",
        overture_category="restaurant",
        osm_tag="amenity=restaurant",
        acceslibre_family="restauration",
    )

    assert category.slug == "restaurant"
    assert mapping.upserts[0].category_id == 10
    assert mapping.upserts[0].osm_tag == "amenity=restaurant"


async def test_map_category_rejects_an_unknown_category(stores: tuple[Any, ...]) -> None:
    categories, _, _, _ = stores

    with pytest.raises(CategoryNotFound):
        await map_category(FakeMappingAdminRepository(), categories, "nope", overture_category="x")
