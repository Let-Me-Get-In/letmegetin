"""Unit tests for the duplicate review use cases (fakes, no database)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from letmegetin.application.places.duplicates import (
    in_review_band,
    merge_duplicate,
    reject_duplicate,
)
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.dedup import AUTO_MATCH_THRESHOLD, REVIEW_MATCH_THRESHOLD
from letmegetin.domain.places.entities import Place, ReviewDecision


def _place(place_id: int, name: str, **kwargs: object) -> Place:
    return Place(id=place_id, name=name, slug=f"slug-{place_id}", source="acceslibre", **kwargs)


class FakePlaces:
    """Only the three methods the review use cases call."""

    def __init__(self, places: dict[int, Place]) -> None:
        self.places = places
        self.decisions: list[ReviewDecision] = []

    async def get_by_id(self, place_id: int) -> Place | None:
        return self.places.get(place_id)

    async def set_review_state(
        self,
        place_id: int,
        canonical_id: int | None,
        duplicate_of_id: int | None,
        operating_status: str,
    ) -> Place:
        updated = replace(
            self.places[place_id],
            canonical_id=canonical_id,
            duplicate_of_id=duplicate_of_id,
            operating_status=operating_status,
        )
        self.places[place_id] = updated
        return updated

    async def add_review_decision(self, decision: ReviewDecision) -> None:
        self.decisions.append(decision)


class FakeAliases:
    def __init__(self) -> None:
        self.rows: list[tuple[int, str]] = []

    async def add(self, place_id: int, name: str) -> None:
        self.rows.append((place_id, name))


class FakeMerges:
    def __init__(self) -> None:
        self.rows: list[tuple[int, int, float, str]] = []

    async def add(
        self, kept_id: int, merged_id: int, score: float, actor: str = "importer"
    ) -> None:
        self.rows.append((kept_id, merged_id, score, actor))


def _review_pair() -> tuple[FakePlaces, FakeAliases, FakeMerges]:
    candidate = _place(1, "Médiathèque Test Alpha")
    place = _place(
        2,
        "Mediatheque Test Alpha Annexe",
        duplicate_of_id=1,
        confidence=0.82,
        operating_status="duplicate_review",
    )
    return FakePlaces({1: candidate, 2: place}), FakeAliases(), FakeMerges()


async def test_merge_refuses_a_place_without_a_pending_candidate() -> None:
    places = FakePlaces({1: _place(1, "Alpha")})

    with pytest.raises(DomainError):
        await merge_duplicate(places, FakeAliases(), FakeMerges(), 1)

    assert places.decisions == []


async def test_reject_refuses_a_place_without_a_pending_candidate() -> None:
    places = FakePlaces({1: _place(1, "Alpha")})

    with pytest.raises(DomainError):
        await reject_duplicate(places, 1)

    assert places.decisions == []


async def test_merge_writes_one_alias_one_merge_log_and_one_decision() -> None:
    places, aliases, merges = _review_pair()

    merged = await merge_duplicate(places, aliases, merges, 2, note="même médiathèque")

    assert merged.canonical_id == 1
    assert merged.duplicate_of_id is None
    assert merged.operating_status == "open"
    assert aliases.rows == [(1, "Mediatheque Test Alpha Annexe")]
    assert merges.rows == [(1, 2, 0.82, "operator")]
    assert places.decisions == [
        ReviewDecision(
            place_id=2,
            candidate_id=1,
            score=0.82,
            decision="merge",
            actor="operator",
            note="même médiathèque",
        )
    ]


async def test_merge_does_not_alias_an_identical_name() -> None:
    candidate = _place(1, "Médiathèque Test Alpha")
    place = _place(2, "MÉDIATHÈQUE TEST ALPHA", duplicate_of_id=1, confidence=0.91)
    places = FakePlaces({1: candidate, 2: place})
    aliases, merges = FakeAliases(), FakeMerges()

    await merge_duplicate(places, aliases, merges, 2)

    assert aliases.rows == []
    assert len(merges.rows) == 1


async def test_reject_writes_one_decision_and_no_merge_log() -> None:
    places, aliases, merges = _review_pair()

    rejected = await reject_duplicate(places, 2, note="annexe distincte")

    assert rejected.canonical_id is None
    assert rejected.duplicate_of_id is None
    assert rejected.operating_status == "open"
    assert aliases.rows == []
    assert merges.rows == []
    assert [(row.decision, row.candidate_id, row.note) for row in places.decisions] == [
        ("reject", 1, "annexe distincte")
    ]


def test_in_review_band_covers_exactly_the_review_bucket() -> None:
    assert in_review_band(REVIEW_MATCH_THRESHOLD)
    assert in_review_band(0.899)
    assert not in_review_band(REVIEW_MATCH_THRESHOLD - 0.001)
    assert not in_review_band(AUTO_MATCH_THRESHOLD)
