"""Criterion use cases driven through in-memory fake repositories (no database)."""

from __future__ import annotations

from typing import Any

import pytest

from letmegetin.application.referential.admin import (
    add_criterion,
    edit_criterion,
    link_criterion,
    set_criterion_families,
    unlink_criterion,
)
from letmegetin.core.exceptions import (
    CategoryNotFound,
    CriterionNotFound,
    DomainError,
)


@pytest.mark.parametrize("kind", ["array", "option", "boolean", "integer", "string"])
async def test_add_criterion_accepts_supported_types(stores: tuple[Any, ...], kind: str) -> None:
    _, criteria, _, _ = stores
    criterion = await add_criterion(criteria, f"new-{kind}", kind, {"fr": kind})
    assert criterion.type == kind


async def test_add_criterion_rejects_unknown_type(stores: tuple[Any, ...]) -> None:
    _, criteria, _, _ = stores
    with pytest.raises(DomainError):
        await add_criterion(criteria, "weird", "date", {"fr": "Weird"})


async def test_add_criterion_resolves_parent_slug(stores: tuple[Any, ...]) -> None:
    _, criteria, _, _ = stores
    criterion = await add_criterion(
        criteria, "entree-acces-rampe", "option", {"fr": "Rampe"}, parent_slug="entree-acces"
    )
    assert criterion.parent_id == 2


async def test_add_criterion_rejects_unknown_parent(stores: tuple[Any, ...]) -> None:
    _, criteria, _, _ = stores
    with pytest.raises(CriterionNotFound):
        await add_criterion(criteria, "x", "option", {"fr": "X"}, parent_slug="nope")


async def test_edit_criterion_flips_default_and_description(stores: tuple[Any, ...]) -> None:
    _, criteria, _, _ = stores
    criteria.items["entree-largeur"].is_default = True

    edited = await edit_criterion(
        criteria,
        "entree-largeur",
        description={"fr": "Largeur utile"},
        is_default=False,
    )

    assert edited.is_default is False
    assert edited.description == {"fr": "Largeur utile"}
    assert edited.label == {"fr": "entree-largeur"}


async def test_link_default_criterion_clears_the_exclusion(stores: tuple[Any, ...]) -> None:
    categories, criteria, mapping, _ = stores
    await unlink_criterion(categories, criteria, mapping, "restaurant", "entree-acces")
    assert mapping.states[(10, 2)] == "exclude"

    await link_criterion(categories, criteria, mapping, "restaurant", "entree-acces")

    assert (10, 2) not in mapping.states
    kept = {node.slug for node in await criteria.list_for_category(10)}
    assert "entree-acces" in kept


async def test_unlink_default_criterion_survives_relisted_defaults(
    stores: tuple[Any, ...],
) -> None:
    categories, criteria, mapping, _ = stores

    await unlink_criterion(categories, criteria, mapping, "restaurant", "entree-acces")

    resolved = {node.slug for node in await criteria.list_for_category(10)}
    assert "entree-acces" not in resolved
    assert "entree-acces-plain-pied" not in resolved
    assert "entree-largeur" in resolved
    assert "entree" in resolved


async def test_link_and_unlink_non_default_criterion(stores: tuple[Any, ...]) -> None:
    categories, criteria, mapping, _ = stores
    extra = await add_criterion(criteria, "extra", "boolean", {"fr": "Extra"})

    await link_criterion(categories, criteria, mapping, "restaurant", "extra")
    assert mapping.states[(10, extra.id)] == "include"
    assert "extra" in {node.slug for node in await criteria.list_for_category(10)}

    await unlink_criterion(categories, criteria, mapping, "restaurant", "extra")
    assert (10, extra.id) not in mapping.states
    assert "extra" not in {node.slug for node in await criteria.list_for_category(10)}


async def test_category_read_keeps_options_of_kept_criteria(stores: tuple[Any, ...]) -> None:
    _, criteria, _, _ = stores
    resolved = {node.slug for node in await criteria.list_for_category(10)}
    assert {"entree", "entree-acces", "entree-acces-plain-pied"} <= resolved


async def test_link_rejects_unknown_slugs(stores: tuple[Any, ...]) -> None:
    categories, criteria, mapping, _ = stores
    with pytest.raises(CategoryNotFound):
        await link_criterion(categories, criteria, mapping, "nope", "entree")
    with pytest.raises(CriterionNotFound):
        await link_criterion(categories, criteria, mapping, "restaurant", "nope")


async def test_set_criterion_families_keeps_the_canonical_order(
    stores: tuple[Any, ...],
) -> None:
    _, criteria, _, _ = stores

    updated = await set_criterion_families(criteria, "entree-acces", ["visuel", "moteur"])

    assert updated.handicap_families == ["moteur", "visuel"]


async def test_set_criterion_families_rejects_an_unknown_family(
    stores: tuple[Any, ...],
) -> None:
    _, criteria, _, _ = stores

    with pytest.raises(DomainError, match="olfactif"):
        await set_criterion_families(criteria, "entree-acces", ["olfactif"])


async def test_edit_criterion_sets_the_en17210_reference(stores: tuple[Any, ...]) -> None:
    _, criteria, _, _ = stores

    edited = await edit_criterion(criteria, "entree-acces", en17210_ref="EN 17210 §5.4")

    assert edited.en17210_ref == "EN 17210 §5.4"
    assert edited.handicap_families == []
