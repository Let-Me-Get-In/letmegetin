"""Functional: ownership, freshness and the write journal on the one answer write path (LIC-04).

Every rule is asserted against the real database and through the shared ``upsert_accessibility``
path, so the Acceslibre import and ``contribute`` inherit exactly the same behaviour (D-09…D-12).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from letmegetin.application.places.contribute import contribute
from letmegetin.application.places.import_acceslibre import (
    import_acceslibre,
    iter_acceslibre_rows,
)
from letmegetin.infrastructure.persistence.repositories import (
    SqlAlchemyCategoryMappingRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyCriterionRepository,
    SqlAlchemyMergeLogRepository,
    SqlAlchemyPlaceAliasRepository,
    SqlAlchemyPlaceRepository,
)
from tests.db import SessionLocal, execute, require_database, row, rows, run, scalar

_PLACE_SOURCE_ID = "test-p12c-place"
_SLUG = "test-p12c-place-00000000"
_CRITERION = "test-p12c-entry"
_OTHER_CRITERION = "test-p12c-width"
_USER_EMAIL = "test-p12c-user@example.test"

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
        await session.execute(
            text(
                "INSERT INTO users (email, password_hash) VALUES (:email, 'test') "
                "ON CONFLICT (email) DO NOTHING"
            ),
            {"email": _USER_EMAIL},
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
    execute("DELETE FROM users WHERE email = :email", {"email": _USER_EMAIL})


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


# --- the same matrix end-to-end, through the importer and ``contribute`` ------------------

_IMPORT_SOURCE_ID = "test-p12c-import"
_IMPORT_CRITERION = "entree-acces"
_NEWER_DATE = "2026-04-01T09:00:00"
_OLDER_DATE = "2026-03-01T09:00:00"
_IMPORT_PARAMS = {"place": _IMPORT_SOURCE_ID, "criterion": _IMPORT_CRITERION}


def _write_csv(path: Path, *, date_maj: str, value: str = "true") -> None:
    path.write_text(
        "id;nom;categorie;date_maj;entree_pmr\n"
        f"{_IMPORT_SOURCE_ID};Lieu Conflit Import;bibliotheque;{date_maj};{value}\n",
        encoding="utf-8",
    )


def _import(path: Path) -> None:
    async def _run() -> None:
        async with SessionLocal() as session:
            await import_acceslibre(
                SqlAlchemyPlaceRepository(session),
                SqlAlchemyCategoryRepository(session),
                SqlAlchemyCategoryMappingRepository(session),
                SqlAlchemyPlaceAliasRepository(session),
                SqlAlchemyMergeLogRepository(session),
                list(iter_acceslibre_rows(path)),
                dedup=False,
            )
            await session.commit()

    run(_run())


def _user_id() -> int:
    return scalar("SELECT id FROM users WHERE email = :email", {"email": _USER_EMAIL})


def _contribute(value: object) -> None:
    slug = scalar(
        "SELECT slug FROM place WHERE source_id = :source_id", {"source_id": _IMPORT_SOURCE_ID}
    )
    user_id = _user_id()

    async def _run() -> None:
        async with SessionLocal() as session:
            await contribute(
                SqlAlchemyPlaceRepository(session),
                SqlAlchemyCriterionRepository(session),
                slug,
                _IMPORT_CRITERION,
                SimpleNamespace(id=user_id),
                value,
            )
            await session.commit()

    run(_run())


def _imported_answer() -> object:
    return row(
        "SELECT pa.value, pa.source, pa.source_license, pa.actor, pa.observed_at "
        "FROM place_accessibility pa JOIN place p ON p.id = pa.place_id "
        "JOIN criteria c ON c.id = pa.criterion_id "
        "WHERE p.source_id = :place AND c.slug = :criterion",
        _IMPORT_PARAMS,
    )


def _imported_journal() -> list[object]:
    return rows(
        "SELECT w.decision, w.reason, w.source, w.value FROM place_accessibility_write w "
        "JOIN place p ON p.id = w.place_id JOIN criteria c ON c.id = w.criterion_id "
        "WHERE p.source_id = :place AND c.slug = :criterion ORDER BY w.id",
        _IMPORT_PARAMS,
    )


def test_a_contribution_takes_ownership_of_an_imported_answer(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    _write_csv(path, date_maj=_NEWER_DATE)
    _import(path)

    _contribute(False)

    written = _imported_answer()
    assert (written.value["value"], written.source, written.actor) == (
        False,
        "user",
        f"user:{_user_id()}",
    )
    assert _imported_journal()[-1].decision == "accepted"


def test_a_reimport_cannot_revert_a_contribution(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    _write_csv(path, date_maj=_NEWER_DATE)
    _import(path)
    _contribute(False)

    _import(path)

    written = _imported_answer()
    assert (written.value["value"], written.source) == (False, "user")
    rejected = _imported_journal()[-1]
    assert (rejected.decision, rejected.reason, rejected.source) == (
        "rejected",
        "other_source",
        "acceslibre",
    )
    assert rejected.value == {"value": "true", "source": "acceslibre", "key": "entree_pmr"}


def test_replaying_the_same_file_keeps_the_value_and_journals_each_attempt(
    db: None, tmp_path: Path
) -> None:
    path = tmp_path / "acceslibre.csv"
    _write_csv(path, date_maj=_NEWER_DATE)
    _import(path)
    first = _imported_answer()

    _import(path)

    replayed = _imported_answer()
    assert (replayed.value, replayed.source, replayed.observed_at) == (
        first.value,
        "acceslibre",
        first.observed_at,
    )
    # D-12: every attempt is journaled — an idempotent replay adds an accepted row and no
    # rejection, and the stored answer never changes.
    assert [entry.decision for entry in _imported_journal()] == ["accepted", "accepted"]


def test_an_older_file_is_rejected_as_stale(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    _write_csv(path, date_maj=_NEWER_DATE)
    _import(path)

    _write_csv(path, date_maj=_OLDER_DATE, value="false")
    _import(path)

    written = _imported_answer()
    assert written.value["value"] == "true"
    rejected = _imported_journal()[-1]
    assert (rejected.decision, rejected.reason) == ("rejected", "stale")
    assert rejected.value["value"] == "false"


def test_an_incoming_null_observed_at_is_rejected_as_stale(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    _write_csv(path, date_maj=_NEWER_DATE)
    _import(path)

    _write_csv(path, date_maj="", value="false")
    _import(path)

    assert _imported_answer().value["value"] == "true"
    rejected = _imported_journal()[-1]
    assert (rejected.decision, rejected.reason) == ("rejected", "stale")
