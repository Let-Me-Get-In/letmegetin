"""Category alias loading and resolution order (DATA-02)."""

from __future__ import annotations

from pathlib import Path

import pytest

from letmegetin.application.places.category_resolution import (
    load_category_aliases,
    resolve_category,
)
from letmegetin.core.exceptions import DomainError

_ALIAS_CSV = """activite;category_slug;places
Bibliothèque médiathèque;library;8759
Musée;museum;1869
Château imaginaire;;1
"""


class _Categories:
    def __init__(self, found: dict[str, int]) -> None:
        self.found = found
        self.calls: list[str] = []

    async def get_by_slug(self, slug: str) -> object | None:
        self.calls.append(slug)
        if slug not in self.found:
            return None
        return type("Category", (), {"id": self.found[slug], "slug": slug})()


class _Mapping:
    def __init__(self, resolved: dict[str, int]) -> None:
        self.resolved = resolved
        self.calls: list[str] = []

    async def resolve_slug(self, slug: str) -> int | None:
        self.calls.append(slug)
        return self.resolved.get(slug)


async def test_alias_hit_uses_the_mapped_category_slug(tmp_path: Path) -> None:
    path = tmp_path / "aliases.csv"
    path.write_text(_ALIAS_CSV, encoding="utf-8")
    aliases = load_category_aliases(path)
    categories = _Categories({"library": 7})
    mapping = _Mapping({})

    resolved = await resolve_category(aliases, categories, mapping, "Bibliothèque médiathèque")

    assert resolved == 7
    assert categories.calls == ["library"]
    assert mapping.calls == []


async def test_alias_falls_back_to_category_mapping(tmp_path: Path) -> None:
    aliases = {"bibliotheque": "books"}
    categories = _Categories({})
    mapping = _Mapping({"books": 42})

    assert await resolve_category(aliases, categories, mapping, "Bibliothèque") == 42
    assert categories.calls == ["books"]
    assert mapping.calls == ["books"]


async def test_direct_category_slug_wins_before_the_ambiguous_mapping() -> None:
    categories = _Categories({"restaurant": 3})
    mapping = _Mapping({"restaurant": 99})  # the mapping bucket is ambiguous and must lose

    assert await resolve_category({}, categories, mapping, "Restaurant") == 3
    assert mapping.calls == []


async def test_unknown_value_resolves_to_none() -> None:
    categories = _Categories({})
    mapping = _Mapping({})

    assert await resolve_category({}, categories, mapping, "Château imaginaire") is None


async def test_none_value_does_no_work() -> None:
    categories = _Categories({})
    mapping = _Mapping({})

    assert await resolve_category({}, categories, mapping, None) is None
    assert await resolve_category({}, categories, mapping, "  ") is None
    assert categories.calls == []


def test_duplicate_source_value_raises(tmp_path: Path) -> None:
    path = tmp_path / "duplicates.csv"
    path.write_text("activite;category_slug\nMusée;museum\nmusee;museum\n", encoding="utf-8")

    with pytest.raises(DomainError, match="duplicate"):
        load_category_aliases(path)


def test_empty_category_rows_are_known_gaps_not_errors(tmp_path: Path) -> None:
    path = tmp_path / "gaps.csv"
    path.write_text(_ALIAS_CSV, encoding="utf-8")

    aliases = load_category_aliases(path)

    assert aliases == {"bibliotheque-mediatheque": "library", "musee": "museum"}
    assert "chateau-imaginaire" not in aliases


def test_committed_alias_file_maps_the_measured_vocabulary() -> None:
    path = Path(__file__).parents[4] / "data" / "referential" / "acceslibre_categories.csv"

    aliases = load_category_aliases(path)

    assert aliases["bibliotheque-mediatheque"] == "library"
    assert aliases["musee"] == "museum"
    assert aliases["mairie"] == "city_hall"
    # Every one of the 391 measured labels is mapped as of 2026-11-09; the file is the
    # single place that knowledge lives, so a shrinking count means a regression.
    assert len(aliases) == 391
