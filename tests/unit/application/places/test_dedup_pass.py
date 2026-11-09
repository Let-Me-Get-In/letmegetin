"""The grid pass: neighbours are paired once, distant twins are left alone."""

from __future__ import annotations

import pytest

from letmegetin.application.places.dedup_pass import recompute_duplicates
from letmegetin.domain.places.entities import DedupRow


class _FakePlaces:
    def __init__(self, rows: list[DedupRow]) -> None:
        self._rows = rows
        self.flagged: list[tuple[int, int, float]] = []
        self.cleared = 0
        self.pending = 0

    async def list_for_dedup(self, limit: int | None = None) -> list[DedupRow]:
        return self._rows

    async def set_duplicate_candidate(self, place_id: int, candidate_id: int, score: float) -> None:
        self.flagged.append((place_id, candidate_id, round(score, 3)))

    async def clear_duplicate_candidates(self) -> int:
        self.cleared += 1
        return self.pending


@pytest.mark.asyncio
async def test_recompute_flags_the_near_twin_once_and_ignores_the_far_one() -> None:
    places = _FakePlaces(
        [
            DedupRow(id=2, name_normalized="pharmacie du centre", lat=45.0, lng=5.0),
            DedupRow(id=1, name_normalized="pharmacie du centre", lat=45.0001, lng=5.0001),
            DedupRow(id=3, name_normalized="pharmacie du centre", lat=48.0, lng=2.0),
        ]
    )

    report = await recompute_duplicates(places)

    assert report.flagged == 1
    assert places.flagged == [(2, 1, 1.0)]


@pytest.mark.asyncio
async def test_recompute_is_a_no_op_on_an_empty_table() -> None:
    places = _FakePlaces([])

    report = await recompute_duplicates(places)

    assert report.places == 0
    assert places.flagged == []


@pytest.mark.asyncio
async def test_recompute_clears_the_previous_queue_before_flagging() -> None:
    # Raising the review floor only takes effect if the rows the last pass flagged go
    # away: measured on dev, 35 903 stale candidates survived a recompute that flagged 11 834.
    places = _FakePlaces(
        [
            DedupRow(id=1, name_normalized="pharmacie du centre", lat=45.0, lng=5.0),
            DedupRow(id=2, name_normalized="pharmacie du centre", lat=45.0001, lng=5.0001),
        ]
    )
    places.pending = 24_069

    report = await recompute_duplicates(places)

    assert places.cleared == 1
    assert report.cleared == 24_069
    assert report.flagged == 1


@pytest.mark.asyncio
async def test_a_dry_run_leaves_the_queue_untouched() -> None:
    places = _FakePlaces(
        [
            DedupRow(id=1, name_normalized="pharmacie du centre", lat=45.0, lng=5.0),
            DedupRow(id=2, name_normalized="pharmacie du centre", lat=45.0001, lng=5.0001),
        ]
    )
    places.pending = 5

    report = await recompute_duplicates(places, dry_run=True)

    assert places.cleared == 0
    assert places.flagged == []
    assert report.flagged == 1
