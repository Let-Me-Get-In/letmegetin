"""Push the answers we own into AccesLibre: read, diff, freshness, patch, journal (D-10..D-12).

The use case depends on the domain ports only (:class:`AccesLibrePushRepositoryPort`,
:class:`AccesLibrePort`) and on the pure decision module; it never imports SQLAlchemy or httpx.
Idempotency is the diff itself: a replayed run reads the value it pushed and writes nothing.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.acceslibre_map import THEIR_FIELD_FOR_SLUG
from letmegetin.domain.places.acceslibre_push import (
    PUSH_FIELDS,
    AccesLibrePort,
    AccesLibrePushRepositoryPort,
    AcceslibrePushWrite,
    OwnedAnswer,
    PushDecision,
    diff_fields,
    freshness_decision,
    push_payload,
    resolve_identifier,
    validate_value,
)

PARTNER_DESTINATION = "lov2_partner"
# The journal's actor: who ran the operator command (never a user id, never their side).
ACTOR = "acceslibre-push"


@dataclass(frozen=True, slots=True)
class PushReport:
    """What the run did: accepted answers, skipped ones, why, and the dry-run diff per ERP."""

    pushed: int
    skipped: int
    skipped_reasons: dict[str, int]
    dry_run: bool
    diffs: dict[str, dict[str, object]] = field(default_factory=dict)


async def push_acceslibre(
    pushes: AccesLibrePushRepositoryPort,
    client: AccesLibrePort,
    *,
    rule: str,
    dry_run: bool = False,
) -> PushReport:
    """Read each ERP once per place, push only what differs, journal every decision."""
    run = _Run(dry_run)
    async for _place_id, answers in _by_place(pushes.stream_owned_answers(PARTNER_DESTINATION)):
        await _push_place(pushes, client, rule=rule, run=run, answers=answers)
    return run.report()


class _Run:
    """Mutable counters for one push, turned into the immutable report at the end."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        self.pushed = 0
        self.skipped = 0
        self.reasons: dict[str, int] = {}
        self.diffs: dict[str, dict[str, object]] = {}

    def skip(self, reason: str) -> None:
        self.skipped += 1
        self.reasons[reason] = self.reasons.get(reason, 0) + 1

    def report(self) -> PushReport:
        return PushReport(
            pushed=self.pushed,
            skipped=self.skipped,
            skipped_reasons=dict(self.reasons),
            dry_run=self.dry_run,
            diffs=dict(self.diffs),
        )


async def _by_place(
    answers: AsyncIterator[OwnedAnswer],
) -> AsyncIterator[tuple[int, list[OwnedAnswer]]]:
    """Group the stream (ordered by canonical place): one GET per place, not per field."""
    place_id: int | None = None
    group: list[OwnedAnswer] = []
    async for answer in answers:
        if place_id is not None and answer.place_id != place_id:
            yield place_id, group
            group = []
        place_id = answer.place_id
        group.append(answer)
    if place_id is not None and group:
        yield place_id, group


async def _push_place(
    pushes: AccesLibrePushRepositoryPort,
    client: AccesLibrePort,
    *,
    rule: str,
    run: _Run,
    answers: list[OwnedAnswer],
) -> None:
    identifier = resolve_identifier(rule, answers[0].erp_slug, answers[0].origin_id)
    if identifier is None:
        await _skip_all(pushes, run, answers, "unmappable")
        return

    fields: dict[str, OwnedAnswer] = {}
    for answer in answers:
        field_name = THEIR_FIELD_FOR_SLUG.get(answer.criterion_slug)
        if field_name is None:
            # One of our criteria AccesLibre's vocabulary cannot express (D-07, D-08).
            await _skip(pushes, run, answer, "unmappable")
            continue
        if not _valid(answer):
            await _skip(pushes, run, answer, "invalid_value")
            continue
        fields[field_name] = answer
    if not fields:
        return

    erp = client.get_erp(identifier)
    section = erp.get("accessibilite")
    theirs = {name: _section_get(section, name) for name in PUSH_FIELDS}
    changed = diff_fields(theirs, {name: answer.value for name, answer in fields.items()})

    their_updated_at = _parse_timestamp(erp.get("updated_at"))
    payload: dict[str, object] = {}
    for name, value in changed.items():
        answer = fields[name]
        decision = freshness_decision(answer.observed_at, answer.recorded_at, their_updated_at)
        if decision == "skip":
            await _skip(pushes, run, answer, "their_fresher")
            continue
        payload[name] = value
    if not payload:
        return

    if run.dry_run:
        run.diffs[identifier] = payload
        return

    try:
        client.patch_erp(identifier, push_payload(payload))
    except DomainError as exc:
        # A 403 is AccesLibre's RPA lock: the ERP accepts no automated write. Keep going.
        if "HTTP 403" in str(exc):
            for name in payload:
                await _skip(pushes, run, fields[name], "rpa_locked")
            return
        raise

    for name in payload:
        run.pushed += 1
        await pushes.append(_journal(fields[name], decision="accepted", reason=None))


async def _skip_all(
    pushes: AccesLibrePushRepositoryPort,
    run: _Run,
    answers: list[OwnedAnswer],
    reason: str,
) -> None:
    for answer in answers:
        await _skip(pushes, run, answer, reason)


async def _skip(
    pushes: AccesLibrePushRepositoryPort,
    run: _Run,
    answer: OwnedAnswer,
    reason: str,
) -> None:
    """Count the skip, and journal it with the value we held — unless this is a dry run."""
    run.skip(reason)
    if not run.dry_run:
        await pushes.append(_journal(answer, decision="skipped", reason=reason))


def _journal(
    answer: OwnedAnswer, *, decision: PushDecision, reason: str | None
) -> AcceslibrePushWrite:
    return AcceslibrePushWrite(
        place_id=answer.place_id,
        criterion_slug=answer.criterion_slug,
        value=dict(answer.value),
        decision=decision,
        reason=reason,
        actor=ACTOR,
        source="user",
        source_license=answer.source_license,
    )


def _stored(answer: OwnedAnswer) -> object:
    return answer.value.get("value") if isinstance(answer.value, dict) else answer.value


def _valid(answer: OwnedAnswer) -> bool:
    """Validate before diffing: ``diff_fields`` normalises and would raise on a bad value."""
    try:
        validate_value(THEIR_FIELD_FOR_SLUG[answer.criterion_slug], _stored(answer))
    except DomainError:
        return False
    return True


def _section_get(section: Any, name: str) -> object:
    return section.get(name) if isinstance(section, dict) else None


def _parse_timestamp(value: object) -> datetime | None:
    """Their ``updated_at`` as a naive UTC datetime, comparable with our stored stamps."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed
