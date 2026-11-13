"""Referential domain entities (pure: no SQLAlchemy, no FastAPI)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Label = dict[str, str]

# The four first-class disability families (Jaccede was motor-only). They live on the
# referential because criteria are the only source of truth for them; places re-export.
HandicapFamily = Literal["moteur", "auditif", "visuel", "mental"]
HANDICAP_FAMILIES: tuple[HandicapFamily, ...] = ("moteur", "auditif", "visuel", "mental")


@dataclass
class Category:
    """A place category (restaurant, hotel, pharmacy…)."""

    id: int
    slug: str
    name: str
    label: Label = field(default_factory=dict)
    parent_id: int | None = None


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
    is_default: bool = False
    handicap_families: list[str] = field(default_factory=list)
    en17210_ref: str | None = None


@dataclass
class VocabularyEntry:
    """A flat vocabulary label, promoted into a criterion on demand."""

    id: int
    slug: str
    label: Label = field(default_factory=dict)
    description: Label = field(default_factory=dict)
    promoted_criterion_id: int | None = None


@dataclass
class AccessibilityFilter:
    """A search filter exposed to API consumers."""

    id: int
    slug: str
    label: Label
    position: int
    handicap_families: list[str] = field(default_factory=list)


@dataclass
class OtherInformation:
    """An official label / complementary information (e.g. Tourisme & Handicap)."""

    id: int
    slug: str
    name: str
    label: Label
    link: str | None = None


@dataclass
class CategoryGrid:
    """A precomputed per-category criteria tree, versioned by the referential version."""

    category_slug: str
    version: int
    tree: list[dict[str, object]]


@dataclass
class CategoryMapping:
    """Our category mapped to the Overture/OSM/Acceslibre vocabularies."""

    category_id: int
    overture_category: str | None = None
    osm_tag: str | None = None
    acceslibre_family: str | None = None
    notes: str | None = None


@dataclass
class Licence:
    """A licence a row may be distributed under (``data/referential/licences.csv``, D-05)."""

    slug: str
    name: str
    url: str | None = None
    obligations: list[str] = field(default_factory=list)


@dataclass
class LicenceDestination:
    """Whether a licence may leave towards a destination (D-06: one reviewed row per pair)."""

    licence_slug: str
    destination: str
    allowed: bool
    note: str | None = None


@dataclass
class SourceLicence:
    """The reviewed source → licence correspondence new writes resolve against (D-07)."""

    source: str
    licence_slug: str
    effective_from: date
