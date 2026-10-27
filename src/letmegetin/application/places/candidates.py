"""Use case: nearby fuzzy candidates, so a new place can reuse an existing record."""

from __future__ import annotations

from letmegetin.domain.places.dedup import similar_score
from letmegetin.domain.places.entities import PlaceHit
from letmegetin.domain.places.repositories import PlaceRepository

MIN_CANDIDATE_SCORE = 0.30


async def find_candidates(
    places: PlaceRepository, lat: float, lng: float, name: str, *, limit: int = 10
) -> list[PlaceHit]:
    """Places within 100 m whose name is close enough to be the same place."""
    nearby = await places.get_candidates(lat, lng, name)
    scored = [
        PlaceHit(
            place=hit.place,
            distance=hit.distance,
            score=round(similar_score(hit.place.name, name), 3),
        )
        for hit in nearby
    ]
    return sorted(
        (hit for hit in scored if hit.score >= MIN_CANDIDATE_SCORE),
        key=lambda hit: hit.score,
        reverse=True,
    )[:limit]
