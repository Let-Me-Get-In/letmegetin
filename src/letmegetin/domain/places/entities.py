"""Place domain entities (pure: no SQLAlchemy, no FastAPI)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from letmegetin.core.utils import slugify
from letmegetin.domain.places.documentation import Documentation
from letmegetin.domain.referential.entities import HANDICAP_FAMILIES, HandicapFamily

__all__ = [
    "HANDICAP_FAMILIES",
    "HandicapFamily",
    "MatchKind",
    "PendingDuplicate",
    "Place",
    "PlaceAccessibility",
    "PlaceHit",
    "PlacePhoto",
    "Review",
    "ReviewDecision",
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
    # Raw source vocabulary value (Acceslibre ``activite``), kept even when unresolved.
    source_category: str | None = None
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
    # Review-queue candidate: what makes the 0.75-0.90 bucket a query, not a recomputation.
    duplicate_of_id: int | None = None
    source_license: str | None = None
    source_url: str | None = None
    retrieved_at: datetime | None = None
    # What the source claims about the data itself (Acceslibre ``date_maj``).
    observed_at: datetime | None = None
    # Read-only projection: filled by the repository when it joins the category.
    category_slug: str | None = None


@dataclass
class PlaceAccessibility:
    """One recorded accessibility value for a place (PLACE-04 skeleton)."""

    criterion_slug: str
    label: dict[str, str] = field(default_factory=dict)
    handicap_families: list[str] = field(default_factory=list)
    value: dict[str, object] = field(default_factory=dict)
    source: str | None = None
    source_license: str | None = None
    # Two dates with two meanings: what the source claims, and when we wrote it (D-02).
    observed_at: datetime | None = None
    recorded_at: datetime | None = None
    actor: str | None = None


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
    # Derived on demand from the grid and the recorded values, never persisted (D-03).
    # ``None`` means "the caller did not ask" (D-07, opt-in).
    documentation: Documentation | None = None


@dataclass(frozen=True, slots=True)
class DedupRow:
    """The minimum a duplicate pass needs: identity, comparable name, position."""

    id: int
    name_normalized: str
    lat: float
    lng: float
    city: str | None = None


@dataclass(frozen=True, slots=True)
class PendingDuplicate:
    """One row of the operator review queue: a place and the candidate it may duplicate."""

    place_id: int
    place_slug: str
    place_name: str
    place_city: str | None
    candidate_id: int
    candidate_slug: str
    candidate_name: str
    score: float


@dataclass
class ReviewDecision:
    """An operator's merge or rejection, kept as the audit trail for both."""

    place_id: int
    candidate_id: int | None
    score: float
    decision: Literal["merge", "reject"]
    actor: str = "operator"
    note: str | None = None


def make_slug(name: str, source: str, source_id: str | None) -> str:
    """Deterministic public slug: readable name plus a short provenance digest."""
    digest = hashlib.sha1(  # noqa: S324 - slug disambiguation only, not a security hash
        f"{source}:{source_id or ''}:{name}".encode(), usedforsecurity=False
    ).hexdigest()[:8]
    return f"{slugify(name)}-{digest}"
