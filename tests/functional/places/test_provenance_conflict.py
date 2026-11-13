"""Functional: ownership, freshness and the write journal on the one answer write path (LIC-04).

Every rule is asserted against the real database and through the shared ``upsert_accessibility``
path, so the Acceslibre import and ``contribute`` inherit exactly the same behaviour (D-09…D-12).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from sqlalchemy import text

from letmegetin.infrastructure.persistence.repositories import SqlAlchemyPlaceRepository
from tests.db import SessionLocal, execute, require_database, row, rows, run

_PLACE_SOURCE_ID = "test-p12c-place"
_SLUG = "test-p12c-place-00000000"
_CRITERION = "test-p12c-entry"
_OTHER_CRITERION = "test-p12c-width"

_CLEANUP = "DELETE FROM place WHERE source_id LIKE 'test-p12c%'"
_PLACE_PARAMS = {"place": _PLACE_SOURCE_ID}


async def _seed() -> None:
    async with SessionLocal() as session:
        for slug in (_CRITERION, _OTHER_CRITERION):
            await session.execute(
                text(
                    "INSERT INTO criteria (slug, parent_id, type, position, need_children, "
                    "label, description) VALUES (:slug, NULL, 'boolean', 0, false, '{}', '{}')"
                ),
                {"slug": slug},
            )
        await session.execute(
            text(
                "INSERT INTO place (source, source_id, name, name_normalized, slug) "
                "VALUES ('acceslibre', :source_id, 'Lieu Conflit', 'lieu conflit', :slug)"
            ),
            {"source_id": _PLACE_SOURCE_ID, "slug": _SLUG},
        )
        await session.commit()


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database(
        "place", "place_accessibility", "place_accessibility_write", "criteria", "source_licence"
    )
    execute(_CLEANUP)
    run(_seed())
    yield
    execute(_CLEANUP)
    execute(
        "DELETE FROM criteria WHERE slug IN (:one, :two)",
        {"one": _CRITERION, "two": _OTHER_CRITERION},
    )


async def _upsert(
    values: dict[str, dict[str, object]],
    *,
    source: str = "acceslibre",
    actor: str = "importer:acceslibre",
    observed_at: datetime | None = None,
) -> None:
    async with SessionLocal() as session:
        places = SqlAlchemyPlaceRepository(session)
        place = await places.get_by_source_id("acceslibre", _PLACE_SOURCE_ID)
        assert place is not None
        await places.upsert_accessibility(
            place.id, values, source=source, actor=actor, observed_at=observed_at
        )
        await session.commit()


def _answer(criterion: str = _CRITERION) -> object:
    return row(
        "SELECT pa.value, pa.source, pa.actor, pa.observed_at FROM place_accessibility pa "
        "JOIN place p ON p.id = pa.place_id JOIN criteria c ON c.id = pa.criterion_id "
        "WHERE p.source_id = :place AND c.slug = :criterion",
        {**_PLACE_PARAMS, "criterion": criterion},
    )


def _journal(criterion: str | None = None) -> list[object]:
    statement = (
        "SELECT w.decision, w.reason, w.source, w.value FROM place_accessibility_write w "
        "JOIN place p ON p.id = w.place_id JOIN criteria c ON c.id = w.criterion_id "
        "WHERE p.source_id = :place"
    )
    params = dict(_PLACE_PARAMS)
    if criterion is not None:
        statement += " AND c.slug = :criterion"
        params["criterion"] = criterion
    return rows(statement + " ORDER BY w.id", params)


def test_an_import_cannot_overwrite_a_user_row(db: None) -> None:
    run(_upsert({_CRITERION: {"value": True}}, source="user", actor="user:7"))
    run(_upsert({_CRITERION: {"value": False}}))

    written = _answer()
    assert (written.value, written.source, written.actor) == ({"value": True}, "user", "user:7")
    rejected = _journal(_CRITERION)[-1]
    assert (rejected.decision, rejected.reason, rejected.source) == (
        "rejected",
        "other_source",
        "acceslibre",
    )
    # The losing value stays visible to an operator (D-12).
    assert rejected.value == {"value": False}


_CURRENT = datetime(2026, 3, 4, 10, 0)
_NEWER = datetime(2026, 3, 5, 10, 0)
_OLDER = datetime(2026, 3, 3, 10, 0)


@pytest.mark.parametrize(
    ("current", "incoming", "decision"),
    [
        # incoming NULL over a set current value: the oldest possible claim (D-10)
        (_CURRENT, None, "rejected"),
        # a set claim over a NULL current value is fresher than nothing
        (None, _NEWER, "accepted"),
        # NULL vs NULL compares equal, so replaying the same file stays idempotent
        (None, None, "accepted"),
        (_CURRENT, _CURRENT, "accepted"),
        (_CURRENT, _NEWER, "accepted"),
        (_CURRENT, _OLDER, "rejected"),
    ],
)
def test_same_source_freshness_treats_null_as_the_oldest(
    db: None, current: datetime | None, incoming: datetime | None, decision: str
) -> None:
    run(_upsert({_CRITERION: {"value": "first"}}, observed_at=current))
    run(_upsert({_CRITERION: {"value": "second"}}, observed_at=incoming))

    last = _journal(_CRITERION)[-1]
    assert last.decision == decision
    assert last.reason == ("stale" if decision == "rejected" else None)
    assert _answer().value == {"value": "first" if decision == "rejected" else "second"}


def test_an_import_inserts_a_missing_criterion_without_overwriting_the_owned_one(
    db: None,
) -> None:
    run(_upsert({_CRITERION: {"value": True}}, source="user", actor="user:7"))
    run(_upsert({_CRITERION: {"value": False}, _OTHER_CRITERION: {"value": 90}}))

    assert _answer(_CRITERION).source == "user"
    inserted = _answer(_OTHER_CRITERION)
    assert (inserted.value, inserted.source) == ({"value": 90}, "acceslibre")
    assert _journal(_OTHER_CRITERION)[-1].decision == "accepted"


def test_a_contribution_takes_ownership_from_another_source(db: None) -> None:
    run(_upsert({_CRITERION: {"value": True}}))
    run(_upsert({_CRITERION: {"value": False}}, source="user", actor="user:7"))

    written = _answer()
    assert (written.value, written.source, written.actor) == ({"value": False}, "user", "user:7")
    accepted = _journal(_CRITERION)[-1]
    assert (accepted.decision, accepted.reason) == ("accepted", None)
