"""Unit tests for the pure AccesLibre push decision (no database, no socket)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.acceslibre_push import (
    diff_fields,
    freshness_decision,
    normalise,
    push_payload,
    resolve_identifier,
    validate_value,
)

_EARLY = datetime(2026, 11, 1, 10, tzinfo=UTC)
_LATE = datetime(2026, 11, 10, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    ("rule", "erp_slug", "origin_id", "expected"),
    [
        ("origin_id", "musee-x", "origin-1", "origin-1"),
        ("slug", "musee-x", "origin-1", "musee-x"),
        ("blocked", "musee-x", "origin-1", None),
        ("slug", None, "origin-1", None),
        ("origin_id", "musee-x", None, None),
    ],
)
def test_resolve_identifier_follows_the_recorded_rule(
    rule: str, erp_slug: str | None, origin_id: str | None, expected: str | None
) -> None:
    assert resolve_identifier(rule, erp_slug, origin_id) == expected


def test_resolve_identifier_refuses_an_unknown_rule() -> None:
    with pytest.raises(DomainError):
        resolve_identifier("guess", "musee-x", "origin-1")


@pytest.mark.parametrize(
    ("value", "field", "expected"),
    [
        ("true", "entree_pmr", True),
        (True, "entree_pmr", True),
        ("oui", "entree_pmr", True),
        ("non", "entree_pmr", False),
        ("12", "entree_marches", 12),
        (12, "entree_marches", 12),
        ("Battante", "entree_porte_manoeuvre", "battante"),
        (None, "entree_pmr", None),
        ("", "entree_pmr", None),
    ],
)
def test_normalise_reads_both_sides_as_one_type(
    value: object, field: str, expected: object
) -> None:
    assert normalise(value, field) == expected


def test_diff_fields_ignores_a_string_versus_boolean_pair() -> None:
    theirs = {"entree_pmr": True, "entree_marches": 2}
    ours = {
        "entree_pmr": {"value": "oui", "source": "user", "user_id": 7},
        "entree_marches": {"value": "2"},
    }

    assert diff_fields(theirs, ours) == {}


def test_diff_fields_returns_our_typed_value_when_it_differs() -> None:
    theirs = {"entree_pmr": True, "sanitaires_presence": None}
    ours = {"entree_pmr": "non", "sanitaires_presence": {"value": "true"}}

    assert diff_fields(theirs, ours) == {"entree_pmr": False, "sanitaires_presence": True}


def test_diff_fields_ignores_a_field_we_hold_no_value_for() -> None:
    assert diff_fields({"entree_pmr": True}, {"entree_pmr": {"value": None}}) == {}


def test_diff_fields_refuses_a_field_outside_the_write_schema() -> None:
    with pytest.raises(DomainError):
        diff_fields({}, {"user_id": {"value": 7}})


def test_freshness_uses_recorded_at_when_observed_at_is_null() -> None:
    """An amended-D-11 claim: a community answer has observed_at NULL and still wins here."""
    assert freshness_decision(None, _LATE, _EARLY) == "push"


def test_freshness_skips_when_their_value_is_newer() -> None:
    assert freshness_decision(None, _EARLY, _LATE) == "skip"


def test_freshness_prefers_observed_at_over_recorded_at() -> None:
    assert freshness_decision(_EARLY, _LATE, _LATE) == "skip"


def test_freshness_pushes_when_the_remote_value_carries_no_date() -> None:
    assert freshness_decision(None, _EARLY, None) == "push"


def test_freshness_skips_when_we_have_no_claim_date() -> None:
    assert freshness_decision(None, None, _LATE) == "skip"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("entree_marches", 40000),
        ("entree_marches", -1),
        ("entree_marches", "two"),
        ("entree_marches", True),
        ("entree_porte_manoeuvre", "pivotante"),
        ("entree_pmr", "peut-être"),
        ("entree_pmr", None),
        ("user_id", 7),
    ],
)
def test_validate_value_refuses_what_the_api_would_coerce(field: str, value: object) -> None:
    with pytest.raises(DomainError):
        validate_value(field, value)


@pytest.mark.parametrize("value", [0, 32767])
def test_validate_value_accepts_the_integer_bounds(value: int) -> None:
    assert validate_value("entree_marches", value) == value


def test_push_payload_wraps_the_schema_key_and_the_wire_value() -> None:
    diff = diff_fields(
        {"entree_pmr": False, "entree_marches": 1},
        {"entree_pmr": "oui", "entree_marches": "2"},
    )

    assert push_payload(diff) == {"accessibilite": {"entree_pmr": "true", "entree_marches": 2}}


def test_push_payload_never_carries_the_stored_user_id() -> None:
    stored = {"value": "oui", "source": "user", "user_id": 42}

    payload = push_payload(diff_fields({}, {"entree_pmr": stored}))

    assert payload == {"accessibilite": {"entree_pmr": "true"}}
    assert "42" not in str(payload)
