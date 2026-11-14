"""Unit: per-place history is folded from the journal's full-row payloads (D-13)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from decimal import Decimal

import pytest
from letmegetin.application.places.history import format_history, place_history

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.export import ExportEvent, _jsonable, describe_changes


def _event(
    seq: int,
    payload: dict[str, object],
    *,
    op: str = "update",
    actor: str = "operator",
) -> ExportEvent:
    return ExportEvent(
        seq=seq,
        occurred_at=datetime(2026, 11, 14, 10, 0),
        entity="place",
        entity_id=1,
        op=op,
        actor=actor,
        payload=payload,
    )


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4}, {"b": 3, "c": 4}),
        ({"a": 1}, {"a": 1}, {}),
        ({"a": 1, "b": 2}, {"a": 1}, {"b": None}),
        ({}, {}, {}),
    ],
)
def test_describe_changes_reports_only_the_keys_that_moved(
    before: dict[str, object], after: dict[str, object], expected: dict[str, object]
) -> None:
    assert describe_changes(before, after) == expected


def test_jsonable_makes_a_row_json_safe() -> None:
    payload = _jsonable(
        {"when": datetime(2026, 11, 14, 10, 0), "ratio": Decimal("0.75"), "name": "Lieu"}
    )

    assert json.loads(json.dumps(payload)) == {
        "when": "2026-11-14T10:00:00+00:00",
        "ratio": 0.75,
        "name": "Lieu",
    }


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_jsonable_refuses_a_non_finite_number(value: float) -> None:
    with pytest.raises(DomainError, match="non-finite"):
        _jsonable({"value": value})


def test_format_history_diffs_each_row_against_the_previous_one() -> None:
    events = [
        _event(1, {"name": "Avant", "city": "Paris"}, op="insert"),
        _event(2, {"name": "Après", "city": "Paris"}),
    ]

    lines = format_history(events)

    assert len(lines) == 2
    assert lines[0].startswith("2026-11-14 insert operator")
    assert "name=Avant" in lines[0]
    assert lines[1].startswith("2026-11-14 update operator")
    assert "name=Après" in lines[1]
    assert "city=" not in lines[1]


class FakeEvents:
    def __init__(self, events: list[ExportEvent]) -> None:
        self.events = events

    async def list_events_by_slug(self, slug: str) -> list[ExportEvent]:
        return self.events


def test_place_history_returns_the_formatted_lines() -> None:
    events = [_event(1, {"name": "Avant"}, op="insert"), _event(2, {"name": "Après"})]

    lines = asyncio.run(place_history(FakeEvents(events), "lieu"))

    assert [line.split()[1] for line in lines] == ["insert", "update"]


def test_place_history_says_so_when_the_journal_is_empty() -> None:
    assert asyncio.run(place_history(FakeEvents([]), "lieu")) == ["no history yet for lieu"]
