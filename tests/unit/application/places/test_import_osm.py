"""Unit tests for the OSM importer: reviewed-tag resolution, dedup bucketing, the report."""

from __future__ import annotations

from pathlib import Path

import pytest

from letmegetin.application.places.import_osm import (
    OsmImportReport,
    import_osm,
    render_unmatched,
    resolve_osm_category,
)
from letmegetin.application.referential.osm_tags import HEADER as OSM_TAGS_HEADER
from letmegetin.config import settings
from letmegetin.domain.places.dedup import (
    AUTO_MATCH_THRESHOLD,
    REVIEW_MATCH_THRESHOLD,
    classify_match,
)
from letmegetin.domain.places.entities import Place, PlaceHit
from letmegetin.domain.places.osm_map import OsmRow

pytestmark = pytest.mark.unit

_CATEGORY_MAP = {"amenity=cafe": 3, "shop=bakery": 4}


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"amenity": "cafe"}, 3),
        ({"name": "Café", "shop": "bakery"}, 4),
        ({"amenity": "bogus"}, None),
        ({"amenity": "bogus", "shop": "bakery"}, 4),
    ],
    ids=["hit", "hit-among-names", "miss", "miss-then-hit"],
)
def test_resolve_osm_category_matches_only_reviewed_pairs(
    tags: dict[str, str], expected: int | None
) -> None:
    assert resolve_osm_category(tags, _CATEGORY_MAP) == expected


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (1.0, "auto"),
        (AUTO_MATCH_THRESHOLD, "auto"),
        (0.899, "review"),
        (REVIEW_MATCH_THRESHOLD, "review"),
        (0.749, "new"),
        (0.0, "new"),
    ],
    ids=["identical", "auto-floor", "below-auto", "review-floor", "below-review", "no-match"],
)
def test_classify_match_buckets_use_the_reviewed_thresholds(score: float, expected: str) -> None:
    assert classify_match(score) == expected


def test_render_unmatched_ranks_by_count_then_tag() -> None:
    report = OsmImportReport(
        unmatched={
            ("name=Café", "amenity=cafe"): 1,
            ("highway=residential",): 3,
            ("amenity=bogus",): 1,
        }
    )

    assert render_unmatched(report) == [
        "  unmatched: highway=residential = 3",
        "  unmatched: amenity=bogus = 1",
        "  unmatched: name=Café|amenity=cafe = 1",
    ]
    assert render_unmatched(report, limit=1) == ["  unmatched: highway=residential = 3"]


class FakePlaces:
    """The place port, in memory: the importer's only dependency with side effects."""

    def __init__(self, candidates: list[Place]) -> None:
        self._candidates = candidates
        self.added: list[Place] = []

    async def get_by_source_id(self, source: str, source_id: str) -> Place | None:
        return None

    async def get_candidates(
        self, lat: float, lng: float, name: str, *, radius: float = 100.0, limit: int = 50
    ) -> list[PlaceHit]:
        return [PlaceHit(place=place, distance=10.0) for place in self._candidates]

    async def add(self, place: Place) -> Place:
        place.id = len(self.added) + 1
        self.added.append(place)
        return place

    async def update(self, place: Place) -> Place:  # pragma: no cover - no row exists yet
        raise AssertionError("the test imports new rows only")

    async def upsert_accessibility(
        self,
        place_id: int,
        values: dict[str, dict[str, object]],
        *,
        source: str,
        actor: str,
        observed_at: object = None,
    ) -> None:  # pragma: no cover - accessibility is 16-02's, already proven
        pass


class FakeMapping:
    async def resolve_osm_tag(self, tag: str) -> int | None:
        return _CATEGORY_MAP.get(tag)


class FakeCategories:
    async def list_all(self) -> list[object]:
        return []


class FakeAliases:
    def __init__(self) -> None:
        self.added: list[tuple[int, str]] = []

    async def add(self, place_id: int, name: str) -> None:
        self.added.append((place_id, name))


class FakeMerges:
    def __init__(self) -> None:
        self.added: list[tuple[int, int, float, str]] = []

    async def add(
        self, kept_id: int, merged_id: int, score: float, actor: str = "importer"
    ) -> None:
        self.added.append((kept_id, merged_id, score, actor))


def _empty_mapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty reviewed accessibility mapping: this file tests the dedup path only."""
    data = tmp_path / "referential"
    data.mkdir()
    (data / "osm_accessibility_tags.csv").write_text(
        f"{';'.join(OSM_TAGS_HEADER)}\n", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "data_dir", data)


async def _import(
    places: FakePlaces, row: OsmRow, **kwargs: bool
) -> tuple[OsmImportReport, FakeMerges, FakeAliases]:
    aliases, merges = FakeAliases(), FakeMerges()
    report = await import_osm(
        places,
        FakeCategories(),
        FakeMapping(),
        aliases,
        merges,
        FakeCategories(),
        [row],
        **kwargs,
    )
    return report, merges, aliases


async def test_import_links_a_nearby_name_match_and_keeps_the_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _empty_mapping(tmp_path, monkeypatch)
    # Accented vs unaccented is the same normalized name: an auto match that keeps an alias.
    candidate = Place(
        id=9, name="Café du Coin", slug="cafe-du-coin", source="acceslibre", lat=45.1, lng=5.1
    )
    places = FakePlaces([candidate])

    report, merges, aliases = await _import(
        places,
        OsmRow("node/1", "Cafe du Coin", 45.1, 5.1, {"amenity": "cafe", "name": "Cafe du Coin"}, 1),
    )

    created = places.added[0]
    assert (created.canonical_id, created.duplicate_of_id) == (9, None)
    assert created.confidence == 1.0
    assert created.operating_status == "open"
    assert report.linked == 1
    assert merges.added == [(9, created.id, 1.0, "osm")]
    assert aliases.added == [(9, "Cafe du Coin")]


async def test_import_diverts_a_weak_match_to_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _empty_mapping(tmp_path, monkeypatch)
    candidate = Place(
        id=9,
        name="Boulangerie du Pain",
        slug="boulangerie-du-pain",
        source="acceslibre",
        lat=45.5,
        lng=5.5,
    )
    places = FakePlaces([candidate])

    report, merges, aliases = await _import(
        places,
        OsmRow(
            "node/3",
            "Boulangerie du Coin",
            45.5,
            5.5,
            {"shop": "bakery", "name": "Boulangerie du Coin"},
            1,
        ),
    )

    created = places.added[0]
    assert (created.canonical_id, created.duplicate_of_id) == (None, 9)
    assert created.operating_status == "duplicate_review"
    assert REVIEW_MATCH_THRESHOLD <= created.confidence < AUTO_MATCH_THRESHOLD
    assert report.review == 1
    assert (merges.added, aliases.added) == ([], [])


async def test_import_no_dedup_never_looks_for_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _empty_mapping(tmp_path, monkeypatch)
    candidate = Place(
        id=9, name="Café du Coin", slug="cafe-du-coin", source="acceslibre", lat=45.1, lng=5.1
    )
    places = FakePlaces([candidate])

    report, merges, aliases = await _import(
        places,
        OsmRow("node/1", "Café du Coin", 45.1, 5.1, {"amenity": "cafe", "name": "Café du Coin"}, 1),
        dedup=False,
    )

    created = places.added[0]
    assert (created.canonical_id, created.confidence, created.operating_status) == (
        None,
        None,
        "open",
    )
    assert (report.linked, report.review) == (0, 0)
    assert (merges.added, aliases.added) == ([], [])
