"""Place domain entities (pure: no SQLAlchemy, no FastAPI)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from letmegetin.core.utils import slugify
from letmegetin.domain.referential.entities import HANDICAP_FAMILIES, HandicapFamily

__all__ = [
    "HANDICAP_FAMILIES",
    "HandicapFamily",
    "MatchKind",
    "Place",
    "PlaceAccessibility",
    "PlaceHit",
    "PlacePhoto",
    "Review",
    "make_slug",
]

MatchKind = Literal["auto", "review", "new"]


@dataclass
class Place:
    """A physical place, whatever its provenance (Acceslibre, Overture, user…)."""

    id: int
    name: str
    slug: str
    source: str
    source_id: str | None = None
    category_id: int | None = None
    address_full: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country_code: str = "FR"
    lat: float | None = None
    lng: float | None = None
    operating_status: str = "open"
    confidence: float | None = None
    website: str | None = None
    phone: str | None = None
    canonical_id: int | None = None
    # Read-only projection: filled by the repository when it joins the category.
    category_slug: str | None = None


@dataclass
class PlaceAccessibility:
    """One recorded accessibility value for a place (PLACE-04 skeleton)."""

    criterion_slug: str
    label: dict[str, str] = field(default_factory=dict)
    handicap_families: list[str] = field(default_factory=list)
    value: dict[str, object] = field(default_factory=dict)


@dataclass
class PlacePhoto:
    """A photo of the place, provenance and license kept explicit."""

    url: str
    credit: str | None = None
    license: str | None = None


@dataclass
class Review:
    """A published review: a 1-5 rating plus optional text."""

    id: int
    rating: int
    body: str
    created: datetime
    author_name: str | None = None
    status: str = "published"


@dataclass
class PlaceHit:
    """A place plus its search metadata: distance in metres and name similarity."""

    place: Place
    distance: float
    score: float = 0.0


def make_slug(name: str, source: str, source_id: str | None) -> str:
    """Deterministic public slug: readable name plus a short provenance digest."""
    digest = hashlib.sha1(  # noqa: S324 - slug disambiguation only, not a security hash
        f"{source}:{source_id or ''}:{name}".encode(), usedforsecurity=False
    ).hexdigest()[:8]
    return f"{slugify(name)}-{digest}"
