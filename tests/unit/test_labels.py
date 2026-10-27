"""Label helpers: parsing, normalization and merging (pure, no database)."""

from __future__ import annotations

import pytest

from letmegetin.core.exceptions import LabelError
from letmegetin.domain.referential.labels import (
    SUPPORTED_LOCALES,
    merge_label,
    normalize_label,
    parse_label_pairs,
)


@pytest.mark.parametrize(
    ("pairs", "expected"),
    [
        (
            ["fr=Restaurant", "en=Restaurant"],
            {"fr": "Restaurant", "en": "Restaurant"},
        ),
        ([" fr = Restaurant "], {"fr": "Restaurant"}),
        (["fr=Porte", "fr=Entrée"], {"fr": "Entrée"}),
        ([], {}),
        (["fr=", "en=Restaurant"], {"en": "Restaurant"}),
    ],
    ids=["two-locales", "trims", "last-wins", "empty", "drops-empty-value"],
)
def test_parse_label_pairs(pairs: list[str], expected: dict[str, str]) -> None:
    assert parse_label_pairs(pairs) == expected


@pytest.mark.parametrize(
    "pairs",
    [["pt=Restaurant"], ["xx=Restaurant"], ["Restaurant"], ["fr"], ["=Restaurant"]],
    ids=["pt", "xx", "no-separator", "locale-only", "empty-locale"],
)
def test_parse_label_pairs_rejects_invalid_input(pairs: list[str]) -> None:
    with pytest.raises(LabelError):
        parse_label_pairs(pairs)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        (
            {"fr": "Restaurant", "en": "Restaurant", "es": "Restaurante"},
            {"fr": "Restaurant", "en": "Restaurant", "es": "Restaurante"},
        ),
        ({"pt": "Restaurante", "fr": "Restaurant"}, {"fr": "Restaurant"}),
        ({"fr": "  ", "it": "Ristorante"}, {"it": "Ristorante"}),
        ({}, {}),
    ],
    ids=["all-supported", "drops-unsupported", "drops-blank", "empty"],
)
def test_normalize_label(label: dict[str, str], expected: dict[str, str]) -> None:
    assert normalize_label(label) == expected


@pytest.mark.parametrize(
    ("current", "overrides", "expected"),
    [
        (
            {"fr": "Restaurant", "en": "Restaurant"},
            {"en": "Dining place"},
            {"fr": "Restaurant", "en": "Dining place"},
        ),
        ({"fr": "Restaurant"}, {"es": "Restaurante", "de": "Restaurant"}, None),
        ({"fr": "Restaurant"}, {}, {"fr": "Restaurant"}),
        ({}, {"fr": "Restaurant"}, {"fr": "Restaurant"}),
    ],
    ids=["overrides-only-given", "adds-locales", "no-override", "from-empty"],
)
def test_merge_label(
    current: dict[str, str], overrides: dict[str, str], expected: dict[str, str] | None
) -> None:
    result = merge_label(current, overrides)
    if expected is None:
        expected = {"fr": "Restaurant", "es": "Restaurante", "de": "Restaurant"}
    assert result == expected


def test_supported_locales_are_the_five_shipped_ones() -> None:
    assert SUPPORTED_LOCALES == ("fr", "en", "es", "de", "it")
