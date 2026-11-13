"""Unit tests for the D-01 documentation ladder (bounds, rounding, answerable leaves)."""

from __future__ import annotations

import pytest

from letmegetin.domain.places.documentation import (
    DOCUMENTATION_LADDER,
    DOCUMENTATION_LEVELS,
    Documentation,
    documentation_level,
    filled_rate,
    leaf_slugs,
    percent_of,
    recorded,
)


def test_levels_are_the_six_slugs_in_order() -> None:
    assert DOCUMENTATION_LEVELS == ("none", "sketch", "partial", "good", "very_good", "complete")


@pytest.mark.parametrize(
    ("percent", "level"),
    [
        (0, "none"),
        (1, "sketch"),
        (10, "sketch"),
        (25, "sketch"),
        (26, "partial"),
        (40, "partial"),
        (50, "partial"),
        (51, "good"),
        (60, "good"),
        (75, "good"),
        (76, "very_good"),
        (90, "very_good"),
        (99, "very_good"),
        (100, "complete"),
    ],
)
def test_level_returns_the_slug_whose_bounds_contain_the_percent(percent: int, level: str) -> None:
    assert documentation_level(percent) == level


def test_level_clamps_percents_outside_the_ladder() -> None:
    assert documentation_level(-3) == "none"
    assert documentation_level(140) == "complete"


@pytest.mark.parametrize(
    ("rate", "percent", "level"),
    [
        (0.0, 0, "none"),
        (0.005, 1, "sketch"),
        (0.25, 25, "sketch"),
        (0.255, 26, "partial"),
        (0.5, 50, "partial"),
        (0.505, 51, "good"),
        (0.75, 75, "good"),
        (0.755, 76, "very_good"),
        (0.99, 99, "very_good"),
        (0.995, 100, "complete"),
        (1.0, 100, "complete"),
    ],
)
def test_from_rate_derives_the_level_from_the_printed_percent(
    rate: float, percent: int, level: str
) -> None:
    documentation = Documentation.from_rate(rate)

    assert (documentation.rate, documentation.percent, documentation.level) == (
        rate,
        percent,
        level,
    )


def test_percent_rounds_half_up_never_half_even() -> None:
    assert percent_of(0.005) == 1
    assert percent_of(0.015) == 2
    assert percent_of(0.255) == 26
    assert percent_of(0.995) == 100


@pytest.mark.parametrize(("slug", "low", "high"), DOCUMENTATION_LADDER)
def test_ladder_bounds_are_a_lockstep_partition(slug: str, low: int, high: int) -> None:
    assert documentation_level(low) == slug
    assert documentation_level(high) == slug
    index = DOCUMENTATION_LEVELS.index(slug)
    if low > 0:
        assert documentation_level(low - 1) == DOCUMENTATION_LEVELS[index - 1]
    if high < 100:
        assert documentation_level(high + 1) == DOCUMENTATION_LEVELS[index + 1]


def test_recorded_counts_false_as_an_answer() -> None:
    assert recorded({"value": False}) is True
    assert recorded({"value": 0}) is True
    assert recorded({"value": None}) is False
    assert recorded(None) is False
    assert recorded("") is False
    assert recorded([]) is False


_OPTION_TREE = [
    {
        "slug": "opt",
        "type": "option",
        "children": [
            {"slug": "opt-a", "type": "option", "children": []},
            {"slug": "opt-b", "type": "option", "children": []},
        ],
    },
    {
        "slug": "grp",
        "type": "array",
        "children": [
            {"slug": "grp-int", "type": "integer", "children": []},
            {
                "slug": "grp-opt",
                "type": "option",
                "children": [{"slug": "grp-opt-a", "type": "option", "children": []}],
            },
        ],
    },
]


def test_leaf_slugs_count_option_criteria_not_their_values() -> None:
    # An option criterion is answerable; its option children are the choice's values.
    # An option criterion under an array group is answerable (AccesLibre stores it there).
    assert leaf_slugs(_OPTION_TREE) == ["opt", "grp-int", "grp-opt"]


def test_filled_rate_divides_by_the_answerable_criteria() -> None:
    values = {"opt": {"value": "yes"}, "opt-a": {"value": "yes"}}

    assert filled_rate(_OPTION_TREE, values) == 0.333


def test_filled_rate_is_zero_without_an_answerable_leaf() -> None:
    assert filled_rate([{"slug": "grp", "type": "array", "children": []}], {}) == 0.0
