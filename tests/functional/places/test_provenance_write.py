"""Functional: every answer and place write stamps provenance from reviewed data (LIC-01/05).

The source → licence correspondence is read from the ``source_licence`` table at write time, so
these tests prove the resolution against the real database and never against a code literal.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from letmegetin.application.places.contribute import contribute
from letmegetin.application.places.import_acceslibre import (
    AcceslibreRow,
    import_acceslibre,
    iter_acceslibre_rows,
)
from letmegetin.core.exceptions import DomainError
from letmegetin.infrastructure.persistence.repositories import (
    SqlAlchemyCategoryMappingRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyCriterionRepository,
    SqlAlchemyMergeLogRepository,
    SqlAlchemyPlaceAliasRepository,
    SqlAlchemyPlaceRepository,
)
from tests.db import SessionLocal, execute, require_database, row, run, scalar

_SOURCE_ID = "test-p12w-place"
_SLUG = "test-p12w-place-00000000"
_CRITERION_SLUG = "test-p12w-crit"
_IMPORTED_SOURCE_ID = "test-p12w-import"
_DATE_MAJ = "2026-03-04T10:30:00"

_CLEANUP = "DELETE FROM place WHERE source_id LIKE 'test-p12w%'"
_PARAMS = {"source_id": _SOURCE_ID, "criterion": _CRITERION_SLUG}


async def _seed() -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
                "description) VALUES (:slug, NULL, 'boolean', 0, false, '{}', '{}')"
            ),
            {"slug": _CRITERION_SLUG},
        )
        await session.execute(
            text(
                "INSERT INTO place (source, source_id, name, name_normalized, slug) "
                "VALUES ('acceslibre', :source_id, 'Lieu Provenance', "
                "'lieu provenance', :slug)"
            ),
            {"source_id": _SOURCE_ID, "slug": _SLUG},
        )
        await session.execute(
            text(
                "INSERT INTO users (email, password_hash) VALUES (:email, 'test') "
                "ON CONFLICT (email) DO NOTHING"
            ),
            {"email": "test-p12w-user@example.test"},
        )
        await session.commit()


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("place", "place_accessibility", "criteria", "source_licence")
    execute(_CLEANUP)
    run(_seed())
    yield
    execute(_CLEANUP)
    execute("DELETE FROM criteria WHERE slug = :slug", {"slug": _CRITERION_SLUG})
    execute("DELETE FROM users WHERE email = 'test-p12w-user@example.test'")


async def _upsert(
    values: dict[str, dict[str, object]],
    *,
    source: str = "acceslibre",
    actor: str = "importer:acceslibre",
    observed_at: datetime | None = None,
) -> None:
    async with SessionLocal() as session:
        places = SqlAlchemyPlaceRepository(session)
        place = await places.get_by_source_id("acceslibre", _SOURCE_ID)
        assert place is not None
        await places.upsert_accessibility(
            place.id, values, source=source, actor=actor, observed_at=observed_at
        )
        await session.commit()


async def _contribute(value: object, user_id: int) -> None:
    async with SessionLocal() as session:
        await contribute(
            SqlAlchemyPlaceRepository(session),
            SqlAlchemyCriterionRepository(session),
            _SLUG,
            _CRITERION_SLUG,
            SimpleNamespace(id=user_id),
            value,
        )
        await session.commit()


async def _import(rows: Sequence[AcceslibreRow]) -> int:
    async with SessionLocal() as session:
        report = await import_acceslibre(
            SqlAlchemyPlaceRepository(session),
            SqlAlchemyCategoryRepository(session),
            SqlAlchemyCategoryMappingRepository(session),
            SqlAlchemyPlaceAliasRepository(session),
            SqlAlchemyMergeLogRepository(session),
            rows,
            dedup=False,
        )
        await session.commit()
        return report.created


def _answer() -> object:
    return row(
        "SELECT pa.source, pa.source_license, pa.actor, pa.observed_at, pa.recorded_at "
        "FROM place_accessibility pa JOIN place p ON p.id = pa.place_id "
        "JOIN criteria c ON c.id = pa.criterion_id "
        "WHERE p.source_id = :source_id AND c.slug = :criterion",
        _PARAMS,
    )


def _write(source: str = "acceslibre", actor: str = "importer:acceslibre") -> object:
    run(_upsert({_CRITERION_SLUG: {"value": True}}, source=source, actor=actor))
    return _answer()


def test_an_acceslibre_write_takes_its_licence_from_the_reviewed_table(db: None) -> None:
    written = _write()
    assert (written.source, written.source_license) == ("acceslibre", "lov2")

    # The mapping is data, not a literal: pointing the source elsewhere changes the snapshot.
    execute(
        "INSERT INTO licence (slug, name, obligations) VALUES "
        "('test-p12w-licence', 'test', '[]'::jsonb) ON CONFLICT (slug) DO NOTHING"
    )
    execute(
        "UPDATE source_licence SET licence_slug = 'test-p12w-licence' WHERE source = 'acceslibre'"
    )
    try:
        assert _write().source_license == "test-p12w-licence"
    finally:
        execute("UPDATE source_licence SET licence_slug = 'lov2' WHERE source = 'acceslibre'")
        execute("DELETE FROM licence WHERE slug = 'test-p12w-licence'")


def test_a_contribution_carries_the_user_licence_never_none(db: None) -> None:
    user_id = scalar(
        "SELECT id FROM users WHERE email = :email", {"email": "test-p12w-user@example.test"}
    )
    run(_contribute(True, user_id))

    written = _answer()
    assert (written.source, written.source_license, written.actor) == (
        "user",
        "odbl",
        f"user:{user_id}",
    )
    assert written.observed_at is None
    assert written.recorded_at is not None


def test_an_unmapped_source_fails_closed(db: None) -> None:
    with pytest.raises(DomainError, match="no reviewed licence"):
        _write(source="unmapped-source", actor="importer:unmapped-source")


def test_an_import_stamps_licence_retrieval_and_the_source_claimed_date(
    db: None, tmp_path: Path
) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(
        "id;nom;categorie;date_maj;entree_pmr\n"
        f"{_IMPORTED_SOURCE_ID};Lieu Importé Provenance;bibliotheque;{_DATE_MAJ};true\n",
        encoding="utf-8",
    )

    assert run(_import(list(iter_acceslibre_rows(path)))) == 1

    place = row(
        "SELECT source_license, retrieved_at, observed_at FROM place WHERE source_id = :source_id",
        {"source_id": _IMPORTED_SOURCE_ID},
    )
    assert place.source_license == "lov2"
    assert place.retrieved_at is not None
    assert place.observed_at == datetime.fromisoformat(_DATE_MAJ)

    answer = row(
        "SELECT pa.source, pa.source_license, pa.actor, pa.observed_at "
        "FROM place_accessibility pa JOIN place p ON p.id = pa.place_id "
        "JOIN criteria c ON c.id = pa.criterion_id WHERE p.source_id = :source_id "
        "AND c.slug = 'entree-acces'",
        {"source_id": _IMPORTED_SOURCE_ID},
    )
    assert (answer.source, answer.source_license, answer.actor) == (
        "acceslibre",
        "lov2",
        "importer:acceslibre",
    )
    assert answer.observed_at == datetime.fromisoformat(_DATE_MAJ)


def test_an_empty_export_date_leaves_observed_at_null(db: None, tmp_path: Path) -> None:
    path = tmp_path / "acceslibre.csv"
    path.write_text(
        f"id;nom;categorie;date_maj\n{_IMPORTED_SOURCE_ID};Lieu Sans Date;bibliotheque;\n",
        encoding="utf-8",
    )

    run(_import(list(iter_acceslibre_rows(path))))

    assert (
        scalar(
            "SELECT observed_at FROM place WHERE source_id = :source_id",
            {"source_id": _IMPORTED_SOURCE_ID},
        )
        is None
    )
