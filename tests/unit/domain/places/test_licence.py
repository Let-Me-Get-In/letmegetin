"""Unit tests for the redistribution predicate (pure, no database).

The matrix is read from the reviewed CSV, so the assertions prove the reviewed data
itself — the LIC-03 row included — and never a rule restated in this file.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from letmegetin.domain.places.licence import DESTINATIONS, can_redistribute

_MATRIX_CSV = Path(__file__).resolve().parents[4] / "data/referential/licence_destinations.csv"


def _reviewed_matrix() -> dict[tuple[str, str], bool]:
    matrix: dict[tuple[str, str], bool] = {}
    with _MATRIX_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            licence = (row.get("licence_slug") or "").strip()
            if licence:
                destination = (row.get("destination") or "").strip()
                matrix[(licence, destination)] = (row.get("allowed") or "").strip() == "true"
    return matrix


_MATRIX = _reviewed_matrix()
_ROWS = [(licence, destination, allowed) for (licence, destination), allowed in _MATRIX.items()]


@pytest.mark.parametrize(
    ("licence", "destination", "allowed"),
    _ROWS,
    ids=[f"{licence}->{destination}" for licence, destination, _ in _ROWS],
)
def test_every_reviewed_row_is_answered_as_reviewed(
    licence: str, destination: str, allowed: bool
) -> None:
    assert can_redistribute(licence, destination, _MATRIX) is allowed


def test_the_lic03_row_is_a_reviewed_denial() -> None:
    assert can_redistribute("odbl", "lov2_partner", _MATRIX) is False


@pytest.mark.parametrize("licence", [None, "", "unknown-licence"])
def test_an_unknown_licence_is_refused(licence: str | None) -> None:
    assert can_redistribute(licence, "open_export", _MATRIX) is False


@pytest.mark.parametrize("destination", [*DESTINATIONS, "unknown-destination"])
def test_a_pair_absent_from_the_matrix_is_refused(destination: str) -> None:
    assert can_redistribute("unknown-licence", destination, _MATRIX) is False


def test_a_missing_matrix_is_refused() -> None:
    assert can_redistribute("lov2", "open_export") is False
