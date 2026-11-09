"""Shared fixtures for the referential admin use-case tests."""

from __future__ import annotations

import pytest

from letmegetin.domain.referential.entities import Category
from tests.unit.application.referential.fakes import (
    FakeCategoryRepository,
    FakeCriterionRepository,
    FakeMappingRepository,
    FakeVocabularyRepository,
    criterion,
)


@pytest.fixture
def stores() -> tuple[
    FakeCategoryRepository,
    FakeCriterionRepository,
    FakeMappingRepository,
    FakeVocabularyRepository,
]:
    mapping = FakeMappingRepository()
    categories = FakeCategoryRepository()
    criteria = FakeCriterionRepository(mapping)
    vocabulary = FakeVocabularyRepository()
    categories.items["restaurant"] = Category(
        id=10, slug="restaurant", name="Restaurant", label={"fr": "Restaurant"}
    )
    criteria.items["entree"] = criterion("entree", 1, kind="array")
    criteria.items["entree-acces"] = criterion("entree-acces", 2, parent_id=1, is_default=True)
    criteria.items["entree-acces-plain-pied"] = criterion(
        "entree-acces-plain-pied", 3, parent_id=2, kind="option"
    )
    criteria.items["entree-largeur"] = criterion("entree-largeur", 4, parent_id=1, is_default=True)
    criteria._next_id = 100
    return categories, criteria, mapping, vocabulary
