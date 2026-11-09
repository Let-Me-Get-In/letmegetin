"""Reclassify re-applies the alias file to places a previous import left uncategorised."""

from __future__ import annotations

import pytest

from letmegetin.application.places.reclassify import reclassify_places
from letmegetin.domain.referential.entities import Category, CategoryMapping


class FakePlaces:
    def __init__(self, pending: dict[str, int], categories: dict[int, int]) -> None:
        self._pending = pending
        self._resolved: dict[int, int] = categories
        self.assigned: dict[str, int] = {}

    async def unresolved_categories(self, limit: int | None = None) -> list[tuple[str, int]]:
        return list(self._pending.items())

    async def reassign_category(self, source_category: str, category_id: int) -> int:
        count = self._pending.pop(source_category, 0)
        self.assigned[source_category] = category_id
        return count


class FakeCategories:
    def __init__(self, by_slug: dict[str, int]) -> None:
        self._by_slug = by_slug

    async def get_by_slug(self, slug: str) -> Category | None:
        if slug not in self._by_slug:
            return None
        return Category(id=self._by_slug[slug], slug=slug, name=slug)


class FakeMapping:
    async def resolve_slug(self, slug: str) -> int | None:
        return None

    async def upsert(self, mapping: CategoryMapping) -> CategoryMapping:  # pragma: no cover
        return mapping


@pytest.mark.asyncio
async def test_reclassify_assigns_the_labels_the_alias_file_now_covers() -> None:
    places = FakePlaces({"Musique": 69, "Inconnu total": 4}, {})
    report = await reclassify_places(
        places, FakeCategories({"music_store": 7}), FakeMapping(), {"musique": "music_store"}
    )

    assert places.assigned == {"Musique": 7}
    assert report.resolved == {"Musique": 69}
    assert report.unresolved == [("Inconnu total", 4)]


@pytest.mark.asyncio
async def test_reclassify_dry_run_reports_without_writing() -> None:
    places = FakePlaces({"Musique": 69}, {})
    report = await reclassify_places(
        places,
        FakeCategories({"music_store": 7}),
        FakeMapping(),
        {"musique": "music_store"},
        dry_run=True,
    )

    assert places.assigned == {}
    assert report.resolved == {"Musique": 69}
    assert report.dry_run is True
