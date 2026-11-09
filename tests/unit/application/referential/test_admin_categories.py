"""Category use cases driven through in-memory fake repositories (no database)."""

from __future__ import annotations

from typing import Any

import pytest

from letmegetin.application.referential.admin import add_category, edit_category
from letmegetin.core.exceptions import CategoryAlreadyExists
from letmegetin.domain.referential.entities import Category


async def test_add_category_rejects_duplicate_slug(
    stores: tuple[Any, ...],
) -> None:
    categories, _, _, _ = stores
    with pytest.raises(CategoryAlreadyExists):
        await add_category(categories, "restaurant", "Restaurant")


async def test_add_category_normalizes_labels(stores: tuple[Any, ...]) -> None:
    categories, _, _, _ = stores
    category = await add_category(categories, "garden", "Garden", {"fr": "Jardin", "pt": "Jardim"})
    assert category.label == {"fr": "Jardin"}


async def test_edit_category_merges_labels_and_reparents(stores: tuple[Any, ...]) -> None:
    categories, _, _, _ = stores
    categories.items["bar"] = Category(id=11, slug="bar", name="Bar", label={"fr": "Bar"})

    edited = await edit_category(
        categories, "restaurant", label={"en": "Restaurant"}, parent_slug="bar"
    )

    assert edited.label == {"fr": "Restaurant", "en": "Restaurant"}
    assert edited.parent_id == 11
    assert edited.name == "Restaurant"
