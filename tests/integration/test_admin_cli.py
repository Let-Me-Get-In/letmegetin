"""Admin CLI integration tests against the real PostGIS database.

Skips cleanly when the container or migration 0002 is absent, so `pytest` still
passes on a machine without Docker.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.config import settings
from letmegetin.infrastructure.persistence.models import CriterionVocabularyModel

# NullPool: each CLI invocation runs its own event loop via asyncio.run, and a pooled
# asyncpg connection cannot be reused from another loop.
_engine = create_async_engine(settings.database_url, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

_SLUGS = ["cli-test-access", "cli-test-ramp", "cli-test-lift"]


async def _database_ready() -> bool:
    try:
        async with _TestSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            table = await session.scalar(text("SELECT to_regclass('criterion_vocabulary')"))
            return table is not None
    except Exception:  # noqa: BLE001 - any connection failure means "skip"
        return False


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if not asyncio.run(_database_ready()):
        pytest.skip("PostGIS database or criterion_vocabulary table unavailable")
    monkeypatch.setattr(admin, "SessionLocal", _TestSessionLocal)
    yield
    asyncio.run(_cleanup())


async def _cleanup() -> None:
    async with _TestSessionLocal() as session:
        await session.execute(text("DELETE FROM categories WHERE slug LIKE 'cli-test-%'"))
        await session.execute(text("DELETE FROM criteria WHERE slug LIKE 'cli-test-%'"))
        await session.execute(text("DELETE FROM criterion_vocabulary WHERE slug LIKE 'cli-test-%'"))
        await session.commit()


async def _count_slugs(slugs: list[str]) -> int:
    async with _TestSessionLocal() as session:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(CriterionVocabularyModel)
                .where(CriterionVocabularyModel.slug.in_(slugs))
            )
            or 0
        )


def _write_entries(path: Path, entries: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_vocabulary_import_is_idempotent(db: None, tmp_path: Path) -> None:
    path = _write_entries(
        tmp_path / "criteria.json",
        [{"slug": slug, "label": {"fr": slug}, "description": {}} for slug in _SLUGS],
    )
    runner = CliRunner()

    first = runner.invoke(admin.app, ["vocabulary", "import", "--file", str(path)])
    assert first.exit_code == 0, first.output
    assert "created=3" in first.output
    assert asyncio.run(_count_slugs(_SLUGS)) == 3

    second = runner.invoke(admin.app, ["vocabulary", "import", "--file", str(path)])
    assert second.exit_code == 0, second.output
    assert "created=0" in second.output
    assert asyncio.run(_count_slugs(_SLUGS)) == 3


def test_vocabulary_import_rejects_entry_without_label(db: None, tmp_path: Path) -> None:
    path = _write_entries(
        tmp_path / "broken.json",
        [{"slug": "cli-test-broken", "label": {}, "description": {}}],
    )
    result = CliRunner().invoke(admin.app, ["vocabulary", "import", "--file", str(path)])

    assert result.exit_code == 1
    output = result.output
    assert "cli-test-broken" in output
    for sql_hint in ("SELECT", "INSERT", "sqlalchemy", "SQLAlchemy"):
        assert sql_hint not in output


def test_admin_cli_curates_categories_criteria_and_mapping(db: None) -> None:
    runner = CliRunner()

    created = runner.invoke(
        admin.app,
        ["category", "add", "cli-test-cat", "--name", "CLI Test", "--label", "fr=Catégorie"],
    )
    assert created.exit_code == 0, created.output

    duplicate = runner.invoke(admin.app, ["category", "add", "cli-test-cat", "--name", "CLI Test"])
    assert duplicate.exit_code == 1
    assert "already exists" in duplicate.output

    edited = runner.invoke(admin.app, ["category", "edit", "cli-test-cat", "--label", "en=Test"])
    assert edited.exit_code == 0, edited.output

    labels = runner.invoke(
        admin.app, ["labels", "set", "category", "cli-test-cat", "--label", "es=Categoría"]
    )
    assert labels.exit_code == 0, labels.output
    assert "es" in labels.output

    listed = runner.invoke(admin.app, ["category", "list"])
    assert listed.exit_code == 0
    assert "cli-test-cat" in listed.output

    group = runner.invoke(
        admin.app,
        ["criterion", "add", "cli-test-entree", "--type", "array", "--label", "fr=Entrée"],
    )
    assert group.exit_code == 0, group.output

    criterion = runner.invoke(
        admin.app,
        [
            "criterion",
            "add",
            "cli-test-acces",
            "--type",
            "boolean",
            "--parent",
            "cli-test-entree",
            "--label",
            "fr=Accès",
            "--default",
        ],
    )
    assert criterion.exit_code == 0, criterion.output

    option = runner.invoke(
        admin.app,
        [
            "criterion",
            "add",
            "cli-test-acces-plain",
            "--type",
            "option",
            "--parent",
            "cli-test-acces",
            "--label",
            "fr=Plain-pied",
        ],
    )
    assert option.exit_code == 0, option.output

    edited_criterion = runner.invoke(
        admin.app,
        [
            "criterion",
            "edit",
            "cli-test-acces",
            "--description",
            "fr=Description",
            "--no-default",
        ],
    )
    assert edited_criterion.exit_code == 0, edited_criterion.output

    orphan = runner.invoke(
        admin.app,
        ["criterion", "add", "cli-test-orphan", "--parent", "cli-test-missing"],
    )
    assert orphan.exit_code == 1
    assert "not found" in orphan.output

    criterion_labels = runner.invoke(
        admin.app, ["labels", "set", "criterion", "cli-test-acces", "--label", "en=Access"]
    )
    assert criterion_labels.exit_code == 0, criterion_labels.output

    linked = runner.invoke(admin.app, ["link", "cli-test-cat", "cli-test-acces"])
    assert linked.exit_code == 0, linked.output

    tree = runner.invoke(admin.app, ["criterion", "list", "--category", "cli-test-cat"])
    assert tree.exit_code == 0, tree.output
    assert "cli-test-acces" in tree.output
    assert "cli-test-acces-plain" in tree.output

    flat = runner.invoke(admin.app, ["criterion", "list", "--flat"])
    assert flat.exit_code == 0
    assert "cli-test-entree" in flat.output

    unlinked = runner.invoke(admin.app, ["unlink", "cli-test-cat", "cli-test-acces"])
    assert unlinked.exit_code == 0, unlinked.output
    after = runner.invoke(admin.app, ["criterion", "list", "--category", "cli-test-cat"])
    assert "cli-test-acces" not in after.output

    unknown_category = runner.invoke(
        admin.app, ["criterion", "list", "--category", "cli-test-nope"]
    )
    assert unknown_category.exit_code == 1
    assert "not found" in unknown_category.output


async def _insert_vocabulary(slug: str, label: dict[str, str], description: dict[str, str]) -> None:
    async with _TestSessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO criterion_vocabulary (slug, label, description) "
                "VALUES (:slug, CAST(:label AS jsonb), CAST(:description AS jsonb))"
            ),
            {
                "slug": slug,
                "label": json.dumps(label),
                "description": json.dumps(description),
            },
        )
        await session.commit()


def test_admin_cli_promotes_vocabulary(db: None) -> None:
    asyncio.run(_insert_vocabulary("cli-test-vocab", {"fr": "Cli test reader"}, {"fr": "Amovible"}))
    runner = CliRunner()

    listed = runner.invoke(admin.app, ["vocabulary", "list", "--query", "cli-test"])
    assert listed.exit_code == 0, listed.output
    assert "cli-test-vocab" in listed.output

    unpromoted = runner.invoke(admin.app, ["vocabulary", "list", "--unpromoted"])
    assert unpromoted.exit_code == 0
    assert "cli-test-vocab" in unpromoted.output

    labels = runner.invoke(
        admin.app, ["labels", "set", "vocabulary", "cli-test-vocab", "--label", "en=Test reader"]
    )
    assert labels.exit_code == 0, labels.output

    created = runner.invoke(admin.app, ["category", "add", "cli-test-promo", "--name", "Promo"])
    assert created.exit_code == 0, created.output

    promoted = runner.invoke(
        admin.app,
        [
            "vocabulary",
            "promote",
            "cli-test-vocab",
            "--type",
            "boolean",
            "--category",
            "cli-test-promo",
        ],
    )
    assert promoted.exit_code == 0, promoted.output

    promoted_list = runner.invoke(admin.app, ["vocabulary", "list", "--query", "cli-test-vocab"])
    assert "-> " in promoted_list.output

    again = runner.invoke(
        admin.app, ["vocabulary", "promote", "cli-test-vocab", "--type", "boolean"]
    )
    assert again.exit_code == 1
    assert "already promoted" in again.output
