"""Pydantic response schemas exposed by the places API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from letmegetin.application.places.get_place import PlaceDetail
from letmegetin.domain.places.entities import Place, PlaceHit


class PlaceSummaryOut(BaseModel):
    """A place in a search result list."""

    slug: str
    name: str
    category: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    distance: float | None = None
    operating_status: str

    @classmethod
    def from_place(cls, place: Place, distance: float | None = None) -> PlaceSummaryOut:
        return cls(
            slug=place.slug,
            name=place.name,
            category=place.category_slug,
            address=place.address_full,
            lat=place.lat,
            lng=place.lng,
            distance=round(distance, 1) if distance is not None else None,
            operating_status=place.operating_status,
        )


class AccessibilityValueOut(BaseModel):
    """One accessibility value recorded for a place."""

    criterion: str
    label: dict[str, str]
    handicap_families: list[str]
    value: dict[str, Any]


class PlaceDetailOut(PlaceSummaryOut):
    """A place record with its accessibility skeleton (PLACE-03/04)."""

    accessibility: list[AccessibilityValueOut] = []
    accessibility_by_family: dict[str, float] = {}

    @classmethod
    def from_detail(cls, detail: PlaceDetail) -> PlaceDetailOut:
        summary = PlaceSummaryOut.from_place(detail.place)
        return cls(
            **summary.model_dump(),
            accessibility=[
                AccessibilityValueOut(
                    criterion=value.criterion_slug,
                    label=value.label,
                    handicap_families=value.handicap_families,
                    value=value.value,
                )
                for value in detail.accessibility
            ],
            accessibility_by_family=detail.accessibility_by_family,
        )


class CandidateOut(BaseModel):
    """A nearby place that may already be the one being created."""

    slug: str
    name: str
    distance: float
    score: float

    @classmethod
    def from_hit(cls, hit: PlaceHit) -> CandidateOut:
        return cls(
            slug=hit.place.slug,
            name=hit.place.name,
            distance=round(hit.distance, 1),
            score=hit.score,
        )
