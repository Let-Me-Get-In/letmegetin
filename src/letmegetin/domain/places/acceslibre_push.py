"""Pure push decision: typed diff, freshness, outbound value validation (D-10, D-11, D-12).

No SQLAlchemy, no httpx, no FastAPI: the adapter implements the port below, the push use case
depends on it, and every rule here is testable without a database or a socket.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from letmegetin.core.exceptions import DomainError

PushDecision = Literal["accepted", "skipped"]
FreshnessDecision = Literal["push", "skip"]

BOOLEAN_FIELDS = frozenset(
    {
        "entree_pmr",
        "accueil_cheminement_plain_pied",
        "sanitaires_presence",
        "stationnement_ext_pmr",
        "transport_station_presence",
    }
)
INTEGER_FIELDS = frozenset({"entree_largeur_mini", "entree_marches"})
INTEGER_MIN = 0
INTEGER_MAX = 32767
PORTE_MANOEUVRE_VALUES = frozenset({"battante", "coulissante", "tourniquet", "tambour"})

# The write schema's 8 writable fields, read from the live OpenAPI on 2026-11-15 (Pitfall 9).
PUSH_FIELDS = BOOLEAN_FIELDS | INTEGER_FIELDS | {"entree_porte_manoeuvre"}


class AccesLibrePort(Protocol):
    """What the push needs from AccesLibre; the httpx adapter is the implementation."""

    def get_erp(self, slug: str) -> dict[str, Any]: ...

    def patch_erp(self, slug: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def list_erps(self, **filters: Any) -> list[dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class OwnedAnswer:
    """One answer we own, with both identifier candidates and the dates freshness needs."""

    place_id: int
    place_slug: str
    criterion_slug: str
    value: dict[str, object]
    observed_at: datetime | None
    recorded_at: datetime
    origin_id: str | None
    erp_slug: str | None


@dataclass(frozen=True, slots=True)
class AcceslibrePushWrite:
    """One append-only journal row; ``value`` keeps the losing side (D-12)."""

    place_id: int
    criterion_slug: str
    value: dict[str, object]
    decision: PushDecision
    reason: str | None
    actor: str


class AccesLibrePushRepositoryPort(Protocol):
    """The owned-answer stream and the outbound journal (D-12)."""

    def stream_owned_answers(self, destination: str) -> AsyncIterator[OwnedAnswer]: ...

    async def append(self, journal: AcceslibrePushWrite) -> None: ...


def resolve_identifier(rule: str, erp_slug: str | None, origin_id: str | None) -> str | None:
    """The identifier the feed and the push key on, from the probe's recorded rule.

    D-05 assumed the importer had stored AccesLibre's ERP slug; it never did — it builds our own
    slug from their ``id`` — so the 15-03 probe records one rule per import and this function is
    the only place that turns it into a key. ``None`` means "unmappable": the row goes to the
    mapping document, because keying on an unverified ``origin_id`` would address the wrong ERP.
    """
    if rule == "origin_id":
        return origin_id
    if rule == "slug":
        return erp_slug
    if rule == "blocked":
        return None
    raise DomainError(f"unknown AccesLibre identifier rule: {rule!r}")


def normalise(value: object, field: str) -> object:
    """Compare-ready value: our stored form and their JSON form become one type (Pitfall 9)."""
    if value is None or value == "":
        return None
    return _typed(field, value)


def validate_value(field: str, value: object) -> object:
    """The outbound value, checked against the write schema; reject, never coerce (Pitfall 7)."""
    if value is None:
        raise DomainError(f"{field}: refusing to send an empty value")
    return _typed(field, value)


def diff_fields(theirs: Mapping[str, object], ours: Mapping[str, object]) -> dict[str, object]:
    """Fields where our typed value differs from theirs, ours only — nothing is deleted (D-10).

    ``ours`` maps a field to a bare value or to the stored ``{"value", "source", …}`` answer;
    only ``value`` is read, so ``user_id`` can never reach the payload (Pitfall 10).
    """
    changed: dict[str, object] = {}
    for field, stored in ours.items():
        if field not in PUSH_FIELDS:
            raise DomainError(f"{field} is not a writable AccesLibre field")
        our_value = normalise(_answer_value(stored), field)
        if our_value is None:
            continue
        if normalise(theirs.get(field), field) != our_value:
            changed[field] = our_value
    return changed


def freshness_decision(
    ours_observed_at: datetime | None,
    ours_recorded_at: datetime | None,
    theirs_updated_at: datetime | None,
) -> FreshnessDecision:
    """Amended D-11: our claim date is ``observed_at``, else ``recorded_at``.

    Phase 12's NULL-is-oldest rule would make every community answer lose to any dated
    AccesLibre value — their ``observed_at`` is always NULL — which defeats PART-02. Their side
    exposes only the ERP-level ``updated_at``, which is coarse: it moves on any ERP edit, not
    only an accessibility one, so a skipped field may be one they never touched.
    """
    claim = ours_observed_at if ours_observed_at is not None else ours_recorded_at
    if claim is None:
        return "skip"
    if theirs_updated_at is None:
        return "push"
    return "push" if claim >= theirs_updated_at else "skip"


def push_payload(diff: Mapping[str, object]) -> dict[str, dict[str, object]]:
    """The PATCH body: the schema's nesting key and only the fields that differ."""
    accessibilite = {
        field: _wire(field, validate_value(field, value)) for field, value in diff.items()
    }
    return {"accessibilite": accessibilite}


def _answer_value(stored: object) -> object:
    if isinstance(stored, Mapping):
        return stored.get("value")
    return stored


def _typed(field: str, value: object) -> object:
    if field in BOOLEAN_FIELDS:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "oui"):
                return True
            if lowered in ("false", "non"):
                return False
        raise DomainError(f"{field}: {value!r} is not a boolean")
    if field in INTEGER_FIELDS:
        number = _as_int(field, value)
        if not INTEGER_MIN <= number <= INTEGER_MAX:
            raise DomainError(f"{field}: {number} is outside {INTEGER_MIN}..{INTEGER_MAX}")
        return number
    if field == "entree_porte_manoeuvre":
        if isinstance(value, str) and value.strip().lower() in PORTE_MANOEUVRE_VALUES:
            return value.strip().lower()
        raise DomainError(f"{field}: {value!r} is not one of {sorted(PORTE_MANOEUVRE_VALUES)}")
    raise DomainError(f"{field} is not a writable AccesLibre field")


def _as_int(field: str, value: object) -> int:
    # ``bool`` is an ``int`` in Python: sending True as a step count would be a silent 1.
    if isinstance(value, bool):
        raise DomainError(f"{field}: {value!r} is not an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise DomainError(f"{field}: {value!r} is not an integer")


def _wire(field: str, value: object) -> object:
    """The live write schema declares booleans as the strings "true"/"false" (Pitfall 9)."""
    if field in BOOLEAN_FIELDS:
        return "true" if value else "false"
    return value
