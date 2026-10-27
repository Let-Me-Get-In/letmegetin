"""Admin use cases driven through in-memory fake repositories (no database)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.application.referential.admin import (
    add_category,
    add_criterion,
    edit_category,
    edit_criterion,
    link_criterion,
    promote_vocabulary,
    set_category_labels,
    set_criterion_labels,
    set_vocabulary_labels,
    unlink_criterion,
)
from letmegetin.core.exceptions import (
    CategoryAlreadyExists,
    CategoryNotFound,
    CriterionNotFound,
    DomainError,
    LabelError,
    NotFoundError,
    VocabularyNotFound,
)
from letmegetin.domain.referential.entities import Category, Criterion, VocabularyEntry


class FakeMappingRepository:
    """Mapping states keyed by (category_id, criterion_id)."""

    def __init__(self) -> None:
        self.states: dict[tuple[int, int], str] = {}

    async def set_state(self, category_id: int, criterion_id: int, state: str) -> None:
        if state == "clear":
            self.states.pop((category_id, criterion_id), None)
        else:
            self.states[(category_id, criterion_id)] = state


class FakeCategoryRepository:
    def __init__(self) -> None:
        self.items: dict[str, Category] = {}
        self._next_id = 1

    async def list_all(self) -> list[Category]:
        return sorted(self.items.values(), key=lambda item: item.slug)

    async def get_by_slug(self, slug: str) -> Category | None:
        return self.items.get(slug)

    async def add(self, category: Category) -> Category:
        stored = replace(category, id=self._next_id)
        self._next_id += 1
        self.items[stored.slug] = stored
        return stored

    async def update(self, category: Category) -> Category:
        self.items.pop(category.slug, None)
        self.items[category.slug] = category
        return category


class FakeCriterionRepository:
    """Resolves a category's applicable set with the documented default/exclusion rule."""

    def __init__(self, mapping: FakeMappingRepository) -> None:
        self.items: dict[str, Criterion] = {}
        self.mapping = mapping
        self._next_id = 1

    async def add(self, criterion: Criterion) -> Criterion:
        stored = replace(criterion, id=self._next_id)
        self._next_id += 1
        self.items[stored.slug] = stored
        return stored

    async def update(self, criterion: Criterion) -> Criterion:
        self.items[criterion.slug] = criterion
        return criterion

    async def list_all(self) -> list[Criterion]:
        return list(self.items.values())

    async def get_by_slug(self, slug: str) -> Criterion | None:
        return self.items.get(slug)

    async def list_for_category(self, category_id: int) -> list[Criterion]:
        states = self.mapping.states
        excluded = {
            cid for (cat, cid), state in states.items() if cat == category_id and state == "exclude"
        }
        included = {
            cid for (cat, cid), state in states.items() if cat == category_id and state == "include"
        }
        resolved = {
            criterion.id
            for criterion in self.items.values()
            if criterion.is_default and criterion.id not in excluded
        } | included
        keep = set(resolved)
        for parent_id in list(resolved):
            keep |= {child.id for child in self.items.values() if child.parent_id == parent_id}
        by_id = {criterion.id: criterion for criterion in self.items.values()}
        for criterion_id in list(keep):
            current = by_id.get(criterion_id)
            while current is not None and current.parent_id is not None:
                keep.add(current.parent_id)
                current = by_id.get(current.parent_id)
        return [criterion for criterion in self.items.values() if criterion.id in keep]


class FakeVocabularyRepository:
    def __init__(self) -> None:
        self.items: dict[str, VocabularyEntry] = {}
        self._next_id = 1

    async def list_all(self) -> list[VocabularyEntry]:
        return sorted(self.items.values(), key=lambda item: item.slug)

    async def get_by_slug(self, slug: str) -> VocabularyEntry | None:
        return self.items.get(slug)

    async def add(self, entry: VocabularyEntry) -> VocabularyEntry:
        stored = replace(entry, id=self._next_id)
        self._next_id += 1
        self.items[stored.slug] = stored
        return stored

    async def update(self, entry: VocabularyEntry) -> VocabularyEntry:
        self.items.pop(entry.slug, None)
        self.items[entry.slug] = entry
        return entry


def _criterion(
    slug: str,
    identifier: int,
    *,
    parent_id: int | None = None,
    is_default: bool = False,
    kind: str = "boolean",
) -> Criterion:
    return Criterion(
        id=identifier,
        slug=slug,
        parent_id=parent_id,
        type=kind,
        position=0,
        label={"fr": slug},
        is_default=is_default,
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
    criteria.items["entree"] = _criterion("entree", 1, kind="array")
    criteria.items["entree-acces"] = _criterion("entree-acces", 2, parent_id=1, is_default=True)
    criteria.items["entree-acces-plain-pied"] = _criterion(
        "entree-acces-plain-pied", 3, parent_id=2, kind="option"
    )
    criteria.items["entree-largeur"] = _criterion("entree-largeur", 4, parent_id=1, is_default=True)
    criteria._next_id = 100
    return categories, criteria, mapping, vocabulary


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


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self) -> _FakeSessionFactory:
        return self

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, *exc: object) -> bool:
        return False


def test_cli_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()

    async def fake_add(repository: Any, slug: str, name: str, label: Any) -> Category:
        return Category(id=1, slug=slug, name=name, label=label)

    monkeypatch.setattr(admin, "add_category", fake_add)
    monkeypatch.setattr(admin, "SessionLocal", _FakeSessionFactory(session))

    result = CliRunner().invoke(admin.app, ["category", "add", "garden", "--name", "Garden"])

    assert result.exit_code == 0, result.output
    assert "garden" in result.output
    assert session.committed


def test_cli_reports_domain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_add(repository: Any, slug: str, name: str, label: Any) -> Category:
        raise CategoryAlreadyExists(slug)

    monkeypatch.setattr(admin, "add_category", fake_add)
    monkeypatch.setattr(admin, "SessionLocal", _FakeSessionFactory(_FakeSession()))

    result = CliRunner().invoke(admin.app, ["category", "add", "garden", "--name", "Garden"])

    assert result.exit_code == 1
    assert "already exists" in result.output
