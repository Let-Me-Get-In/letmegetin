"""Referential domain entities (pure: no SQLAlchemy, no FastAPI)."""

from __future__ import annotations

from dataclasses import dataclass, field

Label = dict[str, str]


@dataclass
class Category:
    """A place category (restaurant, hotel, pharmacy…)."""

    id: int
    slug: str
    name: str
    label: Label = field(default_factory=dict)


@dataclass
class Criterion:
    """A typed, hierarchical accessibility criterion."""

    id: int
    slug: str
    parent_id: int | None
    type: str
    position: int
    label: Label = field(default_factory=dict)
    description: Label = field(default_factory=dict)
    children: list[Criterion] = field(default_factory=list)


@dataclass
class AccessibilityFilter:
    """A search filter exposed to API consumers."""

    id: int
    slug: str
    label: Label
    position: int


@dataclass
class OtherInformation:
    """An official label / complementary information (e.g. Tourisme & Handicap)."""

    id: int
    slug: str
    name: str
    label: Label
    link: str | None = None
