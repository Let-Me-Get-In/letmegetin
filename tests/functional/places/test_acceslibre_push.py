"""Functional: `acceslibre push` reads, diffs, patches and journals idempotently (D-10..D-12).

The AccesLibre boundary is an in-process fake (no socket, no key): the real PostGIS database is
exercised, so the licence-gated stream, the journal rows and the CLI wiring are all real. Only
the outbound HTTP half is substituted — that is the seam 15-02's domain port exists for.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.config import settings
from letmegetin.core.exceptions import DomainError
from letmegetin.infrastructure.persistence.repositories import SqlAlchemyPlaceRepository
from tests.db import SessionLocal, execute, require_database, run, scalar

_PREFIX = "push-test-"
_PLACE_IDS = f"(SELECT id FROM place WHERE slug LIKE '{_PREFIX}%')"
# The 8 writable fields, by our criterion slug (FIELD_MAP's inverse).
_CRITERION = "entree-acces"  # entree_pmr, boolean
_INT_CRITERION = "entree-obstacles-a-la-porte-d-entree"  # entree_marches, integer
_SEEDED_CRITERIA = (_CRITERION, _INT_CRITERION)
_ORIGIN = "push-test-origin-id"
_ERP = "push-test-erp"
_SLUG = f"{_PREFIX}place"


class FakeAccesLibre:
    """``AccesLibrePort`` in process: PATCH applies the value like the real API does."""

    def __init__(
        self,
        accessibilite: dict[str, object] | None = None,
        updated_at: str | None = None,
    ) -> None:
        self.accessibilite = dict(accessibilite or {})
        self.updated_at = updated_at
        self.gets = 0
        self.slugs: list[str] = []
        self.patches: list[dict[str, Any]] = []
        self.locked = False

    def get_erp(self, slug: str) -> dict[str, Any]:
        self.gets += 1
        self.slugs.append(slug)
        return {
            "slug": slug,
            "updated_at": self.updated_at,
            "accessibilite": {**self.accessibilite, "url": "/api/accessibilite/1/"},
        }

    def patch_erp(self, slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.locked:
            # The adapter redacts the body to the status, which is all the use case needs.
            raise DomainError(f"acceslibre refused '{slug}' with HTTP 403")
        self.patches.append(payload)
        self.accessibilite.update(payload["accessibilite"])
        # Build the body directly: a real PATCH is one call, not a PATCH plus a GET.
        return {"slug": slug, "updated_at": self.updated_at, "accessibilite": self.accessibilite}

    def list_erps(self, **filters: Any) -> list[dict[str, Any]]:
        return []

    def close(self) -> None:
        """The CLI closes the adapter it built, exactly as it does a real client."""


def _seed() -> list[int]:
    """The two criteria the push maps, inserted only if the shared referential lacks them."""
    created: list[int] = []
    for slug, kind in ((_CRITERION, "boolean"), (_INT_CRITERION, "integer")):
        found = scalar(
            "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
            "description) VALUES (:slug, NULL, :kind, 0, false, '{}', '{}') "
            "ON CONFLICT (slug) DO NOTHING RETURNING id",
            {"slug": slug, "kind": kind},
        )
        if found is not None:
            created.append(int(found))
    return created


def _cleanup() -> None:
    execute(f"DELETE FROM place WHERE slug LIKE '{_PREFIX}%'")  # cascades answers and journal


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database(
        "place", "place_accessibility", "criteria", "source_licence", "acceslibre_push_write"
    )
    _cleanup()
    created = _seed()
    yield
    _cleanup()
    for criterion_id in created:
        execute("DELETE FROM criteria WHERE id = :id", {"id": criterion_id})


@pytest.fixture
def user_licence(test_sessions: None) -> Iterator[Callable[[str], None]]:
    """Re-stamp the licence `user` answers carry, restoring the reviewed row afterwards.

    The licence is resolved from ``source_licence`` at write time, so this is the real gate:
    ``lov2`` leaves to a lov2 destination, ``cdla`` never does (D-03).
    """
    previous = scalar("SELECT licence_slug FROM source_licence WHERE source = 'user'")

    def set_licence(slug: str) -> None:
        execute(
            "UPDATE source_licence SET licence_slug = :slug WHERE source = 'user'", {"slug": slug}
        )

    yield set_licence
    execute(
        "UPDATE source_licence SET licence_slug = :slug WHERE source = 'user'",
        {"slug": previous},
    )


def _rule(path: Path, monkeypatch: pytest.MonkeyPatch, rule: str) -> None:
    data = path / "referential"
    data.mkdir()
    (data / "acceslibre_identifier_rule.csv").write_text(
        f"rule;detail\n{rule};test\n", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "data_dir", data)


@pytest.fixture
def origin_rule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The probe's `origin_id` rule: our origin_id is the ERP's own key."""
    _rule(tmp_path, monkeypatch, "origin_id")


@pytest.fixture
def blocked_rule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The committed fail-closed default: no identifier we can address an ERP by."""
    _rule(tmp_path, monkeypatch, "blocked")


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> Callable[[FakeAccesLibre], FakeAccesLibre]:
    """Register the in-process fake as the client the CLI builds (the only stubbed seam)."""

    def install(fake: FakeAccesLibre) -> FakeAccesLibre:
        monkeypatch.setattr(admin, "AccesLibreClient", lambda key, transport=None: fake)
        monkeypatch.setattr(settings, "acceslibre_api_key", "test-key")
        return fake

    return install


def _place(*, origin: str = _ORIGIN, slug: str = _SLUG, erp: str = _ERP) -> int:
    execute(
        "INSERT INTO place (source, source_id, name, name_normalized, slug, erp_slug) "
        "VALUES ('acceslibre', :origin, 'Lieu push', 'lieu push', :slug, :erp)",
        {"origin": origin, "slug": slug, "erp": erp},
    )
    place_id = scalar("SELECT id FROM place WHERE slug = :slug", {"slug": slug})
    assert isinstance(place_id, int)
    return place_id


def _answer(place_id: int, values: dict[str, dict[str, object]]) -> None:
    async def write() -> None:
        async with SessionLocal() as session:
            await SqlAlchemyPlaceRepository(session).upsert_accessibility(
                place_id, values, source="user", actor="test"
            )
            await session.commit()

    run(write())


def _push(*args: str) -> Any:
    return CliRunner().invoke(admin.app, ["acceslibre", "push", *args])


def _journal(decision: str | None = None) -> list[tuple[str, str | None, dict[str, Any]]]:
    statement = (
        f"SELECT decision, reason, value FROM acceslibre_push_write WHERE place_id IN {_PLACE_IDS}"
    )
    params: dict[str, Any] = {}
    if decision is not None:
        statement += " AND decision = :decision"
        params["decision"] = decision
    return [(str(row[0]), row[1], row[2]) for row in run(_fetch(statement, params))]


async def _fetch(statement: str, params: dict[str, Any]) -> list[Any]:
    async with SessionLocal() as session:
        return list((await session.execute(text(statement), params)).all())


def _journal_place_ids() -> list[int]:
    statement = (
        f"SELECT place_id FROM acceslibre_push_write WHERE place_id IN {_PLACE_IDS} ORDER BY id"
    )
    return [int(row[0]) for row in run(_fetch(statement, {}))]


def test_dry_run_prints_the_diff_and_writes_nothing(
    origin_rule: None, db: None, user_licence: Callable[[str], None], fake_client: Any
) -> None:
    user_licence("lov2")
    _answer(_place(), {_CRITERION: {"value": True, "source": "user"}})
    fake = fake_client(FakeAccesLibre(accessibilite={"entree_pmr": False}))

    result = _push("--dry-run")

    assert result.exit_code == 0, result.output
    assert "entree_pmr=True" in result.output
    assert fake.patches == []
    assert _journal() == []


def test_a_replayed_push_patches_nothing(
    origin_rule: None, db: None, user_licence: Callable[[str], None], fake_client: Any
) -> None:
    user_licence("lov2")
    _answer(_place(), {_CRITERION: {"value": True, "source": "user"}})
    fake = fake_client(FakeAccesLibre(accessibilite={"entree_pmr": False}))

    first = _push()
    assert first.exit_code == 0, first.output
    assert fake.patches == [{"accessibilite": {"entree_pmr": "true"}}]
    accepted = _journal("accepted")
    assert len(accepted) == 1

    second = _push()

    assert second.exit_code == 0, second.output
    assert fake.patches == [{"accessibilite": {"entree_pmr": "true"}}]
    assert len(_journal("accepted")) == len(accepted)
    assert "pushed=0" in second.output


def test_the_journal_keeps_our_value_on_every_decision(
    origin_rule: None, db: None, user_licence: Callable[[str], None], fake_client: Any
) -> None:
    user_licence("lov2")
    _answer(
        _place(),
        {
            _CRITERION: {"value": True, "source": "user"},
            _INT_CRITERION: {"value": 90, "source": "user"},
        },
    )
    # Their ERP moved after our answers: both fields are theirs (D-11).
    later = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    fake = fake_client(
        FakeAccesLibre(accessibilite={"entree_pmr": False, "entree_marches": 120}, updated_at=later)
    )

    result = _push()

    assert result.exit_code == 0, result.output
    assert fake.patches == []
    kept = _journal("skipped")
    assert len(kept) == 2
    assert {reason for _, reason, _ in kept} == {"their_fresher"}
    assert {row["value"] for _, _, row in kept} == {True, 90}


def test_a_withheld_licence_is_never_pushed(
    origin_rule: None, db: None, user_licence: Callable[[str], None], fake_client: Any
) -> None:
    user_licence("cdla")  # cdla has no lov2_partner grant in the reviewed matrix
    _answer(_place(), {_CRITERION: {"value": True, "source": "user"}})
    fake = fake_client(FakeAccesLibre(accessibilite={"entree_pmr": False}))

    result = _push()

    assert result.exit_code == 0, result.output
    assert fake.gets == 0
    assert fake.patches == []
    assert _journal() == []
    assert "pushed=0" in result.output


def test_a_blocked_rule_journals_unmappable_and_never_patches(
    blocked_rule: None, db: None, user_licence: Callable[[str], None], fake_client: Any
) -> None:
    user_licence("lov2")
    _answer(_place(), {_CRITERION: {"value": True, "source": "user"}})
    fake = fake_client(FakeAccesLibre(accessibilite={"entree_pmr": False}))

    result = _push()

    assert result.exit_code == 0, result.output
    assert fake.gets == 0
    assert fake.patches == []
    assert [(decision, reason) for decision, reason, _ in _journal()] == [("skipped", "unmappable")]


def test_an_out_of_type_value_is_journaled_not_coerced(
    origin_rule: None, db: None, user_licence: Callable[[str], None], fake_client: Any
) -> None:
    user_licence("lov2")
    _answer(_place(), {_CRITERION: {"value": "peut-être", "source": "user"}})
    fake = fake_client(FakeAccesLibre(accessibilite={"entree_pmr": False}))

    result = _push()

    assert result.exit_code == 0, result.output
    assert fake.gets == 0
    assert fake.patches == []
    assert [(decision, reason) for decision, reason, _ in _journal()] == [
        ("skipped", "invalid_value")
    ]


def test_a_locked_erp_is_journaled_and_the_run_continues(
    origin_rule: None, db: None, user_licence: Callable[[str], None], fake_client: Any
) -> None:
    user_licence("lov2")
    _answer(_place(), {_CRITERION: {"value": True, "source": "user"}})
    fake = fake_client(FakeAccesLibre(accessibilite={"entree_pmr": False}))
    fake.locked = True

    result = _push()

    assert result.exit_code == 0, result.output
    assert fake.patches == []
    assert [(decision, reason) for decision, reason, _ in _journal()] == [("skipped", "rpa_locked")]


def test_a_merged_place_pushes_under_its_canonical_identifier(
    origin_rule: None, db: None, user_licence: Callable[[str], None], fake_client: Any
) -> None:
    user_licence("lov2")
    canonical = _place()
    alias = _place(origin="push-test-alias-origin", slug=f"{_PREFIX}alias")
    execute(
        "UPDATE place SET canonical_id = :canonical WHERE id = :alias",
        {"canonical": canonical, "alias": alias},
    )
    _answer(alias, {_CRITERION: {"value": True, "source": "user"}})
    fake = fake_client(FakeAccesLibre(accessibilite={"entree_pmr": False}))

    result = _push()

    assert result.exit_code == 0, result.output
    # The alias's origin_id addresses nothing upstream: the canonical place's does.
    assert fake.slugs == [_ORIGIN]
    assert len(_journal("accepted")) == 1
    assert _journal_place_ids() == [canonical]


def test_a_missing_key_is_a_domain_error(
    origin_rule: None,
    db: None,
    monkeypatch: pytest.MonkeyPatch,
    fake_client: Callable[[FakeAccesLibre], FakeAccesLibre],
) -> None:
    fake_client(FakeAccesLibre())
    monkeypatch.setattr(settings, "acceslibre_api_key", None)

    result = _push()

    assert result.exit_code == 1
    assert "no AccesLibre API key" in result.output
