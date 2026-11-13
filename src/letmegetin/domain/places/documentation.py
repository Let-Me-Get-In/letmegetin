"""How well documented a record is: the D-01 ladder, derived from one integer percent.

Pure domain: no SQLAlchemy, no FastAPI. The server owns the bounds and the slugs once
(D-02); clients map a slug to their localized label and never re-derive a level.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

DocumentationLevel = Literal["none", "sketch", "partial", "good", "very_good", "complete"]

DOCUMENTATION_LEVELS: tuple[DocumentationLevel, ...] = (
    "none",
    "sketch",
    "partial",
    "good",
    "very_good",
    "complete",
)

# (slug, min_pct, max_pct) display bounds per D-01, in whole percent. The same
# integers decide the slug, so the printed percent and the level cannot disagree.
DOCUMENTATION_LADDER: tuple[tuple[DocumentationLevel, int, int], ...] = (
    ("none", 0, 0),
    ("sketch", 1, 25),
    ("partial", 26, 50),
    ("good", 51, 75),
    ("very_good", 76, 99),
    ("complete", 100, 100),
)

_ARRAY_TYPE = "array"
_OPTION_TYPE = "option"
_EMPTY_VALUES: tuple[object, ...] = (None, "", [], {})


def percent_of(rate: float) -> int:
    """The whole percent both the payload and the level use: half-up, never banker's."""
    return min(100, max(0, math.floor(rate * 100 + 0.5)))


def documentation_level(percent: int) -> DocumentationLevel:
    """The slug whose D-01 bounds contain ``percent``, clamped to [0, 100]."""
    clamped = min(100, max(0, percent))
    for level, _, high in DOCUMENTATION_LADDER:
        if clamped <= high:
            return level
    return "complete"  # unreachable: the ladder ends at 100


@dataclass(frozen=True)
class Documentation:
    """A rate and the level derived from the one integer percent it prints."""

    rate: float
    percent: int
    level: DocumentationLevel

    @classmethod
    def from_rate(cls, rate: float) -> Documentation:
        percent = percent_of(rate)
        return cls(rate=rate, percent=percent, level=documentation_level(percent))


def recorded(value: object) -> bool:
    """A criterion is filled when a real value is recorded (False still counts as an answer)."""
    if not isinstance(value, dict):
        return value not in _EMPTY_VALUES
    return value.get("value") not in _EMPTY_VALUES


def answerable_criteria(
    nodes: list[dict[str, Any]], parent_type: str | None = None
) -> list[dict[str, Any]]:
    """Grid nodes that can carry a value.

    ``array`` nodes are groups, not answers; an option's children are its choice values,
    not criteria — except under an array parent, where AccesLibre stores an answer.
    """
    answerable: list[dict[str, Any]] = []
    for node in nodes:
        node_type = str(node.get("type"))
        if node_type != _ARRAY_TYPE and not (
            node_type == _OPTION_TYPE and parent_type == _OPTION_TYPE
        ):
            answerable.append(node)
        answerable.extend(answerable_criteria(node.get("children") or [], node_type))
    return answerable


def leaf_slugs(nodes: list[dict[str, Any]]) -> list[str]:
    """The slugs of the grid's answerable criteria, in tree order."""
    return [str(node["slug"]) for node in answerable_criteria(nodes)]


def filled_rate(tree: list[dict[str, Any]], values: dict[str, dict[str, Any]]) -> float:
    """Share of the grid's answerable criteria that carry a recorded value."""
    leaves = leaf_slugs(tree)
    if not leaves:
        return 0.0
    filled = [slug for slug in leaves if slug in values and recorded(values[slug])]
    return round(len(set(filled)) / len(leaves), 3)
