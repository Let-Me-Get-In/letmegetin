"""Operator duplicate review: list the candidates the importer flagged, merge or reject them.

Merging stays soft (``canonical_id`` + alias + merge log), so clearing ``canonical_id``
restores the previous state. A rejection keeps both rows. Both decisions are appended to
``place_review_decision`` — the only audit trail for rejections, since ``place_merge_log``
covers merges only.
"""

from __future__ import annotations

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.dedup import AUTO_MATCH_THRESHOLD, REVIEW_MATCH_THRESHOLD
from letmegetin.domain.places.entities import PendingDuplicate, Place, ReviewDecision
from letmegetin.domain.places.repositories import (
    MergeLogRepository,
    PlaceAliasRepository,
    PlaceRepository,
)


def in_review_band(score: float) -> bool:
    """Whether a stored score still belongs to the review bucket (0.75 ≤ s < 0.90)."""
    return REVIEW_MATCH_THRESHOLD <= score < AUTO_MATCH_THRESHOLD


async def list_pending(places: PlaceRepository, limit: int = 50) -> list[PendingDuplicate]:
    """The review queue, best score first; out-of-band rows are listed, never hidden."""
    return await places.list_pending_reviews(limit)


async def _pending(places: PlaceRepository, place_id: int) -> tuple[Place, int]:
    place = await places.get_by_id(place_id)
    if place is None:
        raise DomainError(f"place #{place_id} does not exist")
    if place.duplicate_of_id is None:
        raise DomainError(f"place #{place_id} has no pending duplicate candidate")
    return place, place.duplicate_of_id


async def merge_duplicate(
    places: PlaceRepository,
    aliases: PlaceAliasRepository,
    merges: MergeLogRepository,
    place_id: int,
    *,
    note: str | None = None,
    actor: str = "operator",
) -> Place:
    """Link the place to its candidate exactly like the importer's auto-link."""
    place, candidate_id = await _pending(places, place_id)
    candidate = await places.get_by_id(candidate_id)
    if candidate is None:
        raise DomainError(f"candidate #{candidate_id} for place #{place_id} does not exist")

    score = place.confidence or 0.0
    merged = await places.set_review_state(place.id, candidate.id, None, "open")
    if candidate.name.casefold() != place.name.casefold():
        await aliases.add(candidate.id, place.name)
    await merges.add(candidate.id, place.id, score, actor=actor)
    await places.add_review_decision(
        ReviewDecision(
            place_id=place.id,
            candidate_id=candidate.id,
            score=score,
            decision="merge",
            actor=actor,
            note=note,
        )
    )
    return merged


async def reject_duplicate(
    places: PlaceRepository,
    place_id: int,
    *,
    note: str | None = None,
    actor: str = "operator",
) -> Place:
    """Drop the candidate but keep both places: the queue must not resurface the pair."""
    place, candidate_id = await _pending(places, place_id)
    rejected = await places.set_review_state(place.id, place.canonical_id, None, "open")
    await places.add_review_decision(
        ReviewDecision(
            place_id=place.id,
            candidate_id=candidate_id,
            score=place.confidence or 0.0,
            decision="reject",
            actor=actor,
            note=note,
        )
    )
    return rejected
