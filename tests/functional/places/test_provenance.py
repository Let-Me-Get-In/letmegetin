"""Functional: migration 0011 backfills provenance from the reviewed CSV (D-04, LIC-05).

The rows are inserted at the 0010 schema, then the migration is applied, so the
backfill is proven against data that pre-existed it — never against its own output.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
from pathlib import Path

from sqlalchemy import text

from letmegetin.config import settings
from tests.db import SessionLocal, require_database, row, run, scalar

_ROOT = Path(__file__).resolve().parents[3]
_SOURCE_LICENCES = _ROOT / "data/referential/source_licences.csv"

_SOURCE_ID = "test-provenance-1"
_CRITERION_SLUG = "test-provenance-crit"
# The shape `contribute` writes today: the source and the actor are already in the value.
_ANSWER_VALUE = {"value": "true", "source": "user", "user_id": 4242}

_NULL_LICENCES = (
    "SELECT count(*) FROM place WHERE source_license IS NULL",
    "SELECT count(*) FROM place_accessibility WHERE source_license IS NULL",
)


def _reviewed_mapping() -> dict[str, str]:
    """The expected mapping comes from the same file the migration reads (LIC-05)."""
    with _SOURCE_LICENCES.open(encoding="utf-8", newline="") as handle:
        return {
            row["source"].strip(): row["licence_slug"].strip()
            for row in csv.DictReader(handle, delimiter=";")
            if (row.get("source") or "").strip()
        }


def _alembic(*args: str) -> None:
    env = {**os.environ, "LETMEGETIN_DATABASE_URL": settings.database_url}
    subprocess.run(
        ["uv", "run", "alembic", *args],
        cwd=_ROOT,
        env=env,
        check=True,
        capture_output=True,
    )


async def _seed() -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
                "description, handicap_families) VALUES (:slug, NULL, 'boolean', 0, false, "
                "'{}', '{}', ARRAY['moteur'])"
            ),
            {"slug": _CRITERION_SLUG},
        )
        await session.execute(
            text(
                "INSERT INTO place (source, source_id, name, name_normalized, slug) "
                "VALUES ('acceslibre', :source_id, 'Test Provenance', "
                "'test provenance', 'test-provenance-place')"
            ),
            {"source_id": _SOURCE_ID},
        )
        await session.execute(
            text(
                "INSERT INTO place_accessibility (place_id, criterion_id, value) "
                "SELECT p.id, c.id, CAST(:value AS jsonb) FROM place p, criteria c "
                "WHERE p.source_id = :source_id AND c.slug = :criterion"
            ),
            {
                "source_id": _SOURCE_ID,
                "criterion": _CRITERION_SLUG,
                "value": json.dumps(_ANSWER_VALUE),
            },
        )
        await session.commit()


async def _cleanup() -> None:
    async with SessionLocal() as session:
        await session.execute(
            text("DELETE FROM place WHERE source_id = :source_id"), {"source_id": _SOURCE_ID}
        )
        await session.execute(
            text("DELETE FROM criteria WHERE slug = :slug"), {"slug": _CRITERION_SLUG}
        )
        await session.commit()


def test_backfill_resolves_every_source_from_reviewed_data() -> None:
    require_database("place", "place_accessibility", "criteria")
    expected = _reviewed_mapping()

    try:
        _alembic("downgrade", "0010")
        run(_seed())
        _alembic("upgrade", "head")

        assert (
            scalar(
                "SELECT source_license FROM place WHERE source_id = :source_id",
                {"source_id": _SOURCE_ID},
            )
            == expected["acceslibre"]
        )
        answer = row(
            "SELECT a.source, a.source_license, a.actor "
            "FROM place_accessibility a JOIN place p ON p.id = a.place_id "
            "WHERE p.source_id = :source_id",
            {"source_id": _SOURCE_ID},
        )
        assert answer.source == "user"
        assert answer.source_license == expected["user"]
        assert answer.actor == "user:4242"

        for statement in _NULL_LICENCES:
            assert scalar(statement) == 0
        assert (
            scalar("SELECT count(*) FROM place_accessibility WHERE source IS NULL OR source = ''")
            == 0
        )

        for table in ("licence", "licence_destination", "source_licence"):
            assert scalar("SELECT to_regclass(:table)", {"table": table}) is not None
    finally:
        _alembic("upgrade", "head")
        run(_cleanup())
