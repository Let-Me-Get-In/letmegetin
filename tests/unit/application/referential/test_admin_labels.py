"""Label-setter use cases driven through fake repositories (no database)."""

from __future__ import annotations

from typing import Any

import pytest

from letmegetin.application.referential.admin import (
    set_category_labels,
    set_criterion_labels,
    set_vocabulary_labels,
)
from letmegetin.core.exceptions import LabelError, NotFoundError
from letmegetin.domain.referential.entities import VocabularyEntry


async def test_label_setters_merge_per_kind(stores: tuple[Any, ...]) -> None:
    categories, criteria, _, vocabulary = stores
    await vocabulary.add(VocabularyEntry(id=0, slug="rampe", label={"fr": "Rampe", "it": "Rampa"}))

    category = await set_category_labels(categories, "restaurant", {"en": "Restaurant"})
    criterion = await set_criterion_labels(criteria, "entree-acces", {"en": "Access"})
    entry = await set_vocabulary_labels(vocabulary, "rampe", {"en": "Ramp"})

    assert category.label == {"fr": "Restaurant", "en": "Restaurant"}
    assert criterion.label == {"fr": "entree-acces", "en": "Access"}
    assert entry.label == {"fr": "Rampe", "en": "Ramp", "it": "Rampa"}


@pytest.mark.parametrize(
    "call",
    [
        lambda stores: set_category_labels(stores[0], "nope", {"fr": "X"}),
        lambda stores: set_criterion_labels(stores[1], "nope", {"fr": "X"}),
        lambda stores: set_vocabulary_labels(stores[3], "nope", {"fr": "X"}),
    ],
    ids=["category", "criterion", "vocabulary"],
)
async def test_label_setters_raise_for_unknown_slug(stores: tuple[Any, ...], call: Any) -> None:
    with pytest.raises(NotFoundError):
        await call(stores)


async def test_set_labels_rejects_unsupported_locale(stores: tuple[Any, ...]) -> None:
    from letmegetin.domain.referential.labels import parse_label_pairs

    with pytest.raises(LabelError):
        parse_label_pairs(["pt=Restaurante"])
