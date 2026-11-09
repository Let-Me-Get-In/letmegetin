"""In-memory repositories used by the referential admin use-case tests."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from letmegetin.domain.referential.entities import (
    Category,
    CategoryMapping,
    Criterion,
    VocabularyEntry,
)


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


class FakeMappingAdminRepository:
    def __init__(self) -> None:
        self.upserts: list[CategoryMapping] = []

    async def upsert(self, mapping: CategoryMapping) -> None:
        self.upserts.append(mapping)


class FakeCategoryGridRepository:
    def __init__(self) -> None:
        self.version = 1
        self.grids: dict[int, tuple[int, list[dict[str, object]]]] = {}

    async def current_version(self) -> int:
        return self.version

    async def bump_version(self) -> int:
        self.version += 1
        return self.version

    async def set_grid(self, category_id: int, version: int, tree: list[dict[str, object]]) -> None:
        self.grids[category_id] = (version, tree)

    async def get_for_slug(self, slug: str) -> Any:
        return None


def criterion(
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
