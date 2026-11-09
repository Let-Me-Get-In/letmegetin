"""Vocabulary promotion use cases driven through fake repositories (no database)."""

from __future__ import annotations

from typing import Any

import pytest

from letmegetin.application.referential.admin import promote_vocabulary
from letmegetin.core.exceptions import DomainError, VocabularyNotFound
from letmegetin.domain.referential.entities import VocabularyEntry


async def test_promote_vocabulary_creates_and_links_a_criterion(
    stores: tuple[Any, ...],
) -> None:
    categories, criteria, mapping, vocabulary = stores
    await vocabulary.add(
        VocabularyEntry(
            id=0,
            slug="lecteur-de-carte",
            label={"fr": "Lecteur de carte bancaire"},
            description={"fr": "Un lecteur amovible"},
        )
    )

    criterion = await promote_vocabulary(
        vocabulary,
        criteria,
        mapping,
        categories,
        "lecteur-de-carte",
        "boolean",
        category_slugs=["restaurant"],
    )

    assert criterion.label == {"fr": "Lecteur de carte bancaire"}
    assert criterion.description == {"fr": "Un lecteur amovible"}
    assert vocabulary.items["lecteur-de-carte"].promoted_criterion_id == criterion.id
    assert mapping.states[(10, criterion.id)] == "include"


async def test_promote_vocabulary_twice_is_refused(stores: tuple[Any, ...]) -> None:
    categories, criteria, mapping, vocabulary = stores
    await vocabulary.add(VocabularyEntry(id=0, slug="rampe", label={"fr": "Rampe"}))
    await promote_vocabulary(
        vocabulary, criteria, mapping, categories, "rampe", "boolean", category_slugs=[]
    )

    with pytest.raises(DomainError):
        await promote_vocabulary(
            vocabulary, criteria, mapping, categories, "rampe", "boolean", category_slugs=[]
        )


async def test_promote_vocabulary_unknown_slug(stores: tuple[Any, ...]) -> None:
    categories, criteria, mapping, vocabulary = stores
    with pytest.raises(VocabularyNotFound):
        await promote_vocabulary(
            vocabulary, criteria, mapping, categories, "nope", "boolean", category_slugs=[]
        )
