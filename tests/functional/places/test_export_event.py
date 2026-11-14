"""Functional: the export journal records every place write, in the write's transaction.

Runs against the real PostGIS test database: the guarantees here (same-transaction append,
nothing for a rejected or no-op write, the MVCC boundary) can only be proven by PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.domain.places.entities import Place
from letmegetin.infrastructure.persistence.export_repositories import (
    SqlAlchemyExportEventRepository,
)
from letmegetin.infrastructure.persistence.models import ExportEventModel
from letmegetin.infrastructure.persistence.repositories import SqlAlchemyPlaceRepository
from tests.db import SessionLocal, execute, require_database, row, run, scalar

_SOURCE = "acceslibre"
_PREFIX = "cli-test-export-"
_CRITERION = "cli-test-export-crit"
_OTHER_CRITERION = "cli-test-export-crit-other"
_UNRESOLVED = "cli-test-export-cat"
_CATEGORY = "cli-test-export-category"

_PLACE_IDS = f"(SELECT id FROM place WHERE slug LIKE '{_PREFIX}%')"


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("export_event", "place", "criteria", "source_licence")
    _cleanup()
    _seed()
    yield
    _cleanup()


def _cleanup() -> None:
    # export_event has no foreign key: it must go first, then the place cascade clears
    # the answers, the write journal, aliases and review decisions.
    execute(f"DELETE FROM export_event WHERE entity_id IN {_PLACE_IDS}")
    execute(f"DELETE FROM place WHERE slug LIKE '{_PREFIX}%'")
    execute(f"DELETE FROM criteria WHERE slug LIKE '{_PREFIX}%'")
    execute(f"DELETE FROM categories WHERE slug LIKE '{_PREFIX}%'")


def _seed() -> None:
    for slug in (_CRITERION, _OTHER_CRITERION):
        execute(
            "INSERT INTO criteria (slug, parent_id, type, position, need_children, label, "
            "description) VALUES (:slug, NULL, 'boolean', 0, false, '{}', '{}') "
            "ON CONFLICT (slug) DO NOTHING",
            {"slug": slug},
        )
    execute(
        "INSERT INTO categories (slug, name, label) VALUES (:slug, 'Test', '{}') "
        "ON CONFLICT (slug) DO NOTHING",
        {"slug": _CATEGORY},
    )


async def _add(source_id: str, name: str, **kwargs: object) -> Place:
    async with SessionLocal() as session:
        place = await SqlAlchemyPlaceRepository(session).add(
            Place(
                id=0,
                name=name,
                slug=f"{_PREFIX}{source_id}",
                source=_SOURCE,
                source_id=source_id,
                **kwargs,
            )
        )
        await session.commit()
        return place


async def _rename(place_id: int, name: str) -> None:
    async with SessionLocal() as session:
        repository = SqlAlchemyPlaceRepository(session)
        place = await repository.get_by_id(place_id)
        assert place is not None
        place.name = name
        await repository.update(place)
        await session.commit()


async def _review(place_id: int, canonical_id: int | None, duplicate_of_id: int | None) -> None:
    async with SessionLocal() as session:
        await SqlAlchemyPlaceRepository(session).set_review_state(
            place_id, canonical_id, duplicate_of_id, "open"
        )
        await session.commit()


async def _upsert(
    place_id: int,
    values: dict[str, dict[str, object]],
    *,
    observed_at: datetime | None = None,
) -> None:
    async with SessionLocal() as session:
        await SqlAlchemyPlaceRepository(session).upsert_accessibility(
            place_id,
            values,
            source=_SOURCE,
            actor=f"importer:{_SOURCE}",
            observed_at=observed_at,
        )
        await session.commit()


def _events(place_id: int) -> list[ExportEventModel]:
    async def read() -> list[ExportEventModel]:
        async with SessionLocal() as session:
            return list(
                (
                    await session.scalars(
                        select(ExportEventModel)
                        .where(ExportEventModel.entity_id == place_id)
                        .order_by(ExportEventModel.seq)
                    )
                ).all()
            )

    return run(read())


def test_add_appends_one_insert_event_with_the_full_row(db: None) -> None:
    place = run(_add("add", "Lieu Journal Un"))

    events = _events(place.id)

    assert [(event.entity, event.op, event.entity_id) for event in events] == [
        ("place", "insert", place.id)
    ]
    payload = events[0].payload
    assert payload["slug"] == place.slug
    assert payload["name"] == "Lieu Journal Un"
    assert payload["source_license"] == "lov2"
    # The journal stores the referential row, not derived or bookkeeping columns.
    for excluded in ("location", "name_normalized", "created", "updated"):
        assert excluded not in payload


def test_update_appends_a_second_event_with_the_new_name(db: None) -> None:
    place = run(_add("update", "Lieu Journal Avant"))
    run(_rename(place.id, "Lieu Journal Après"))

    events = _events(place.id)

    assert [event.op for event in events] == ["insert", "update"]
    assert events[1].payload["name"] == "Lieu Journal Après"


def test_merge_appends_one_merge_event(db: None) -> None:
    target = run(_add("merge-target", "Lieu Cible"))
    candidate = run(_add("merge-candidate", "Lieu Doublon"))

    run(_review(candidate.id, target.id, None))

    events = _events(candidate.id)
    assert [event.op for event in events] == ["insert", "merge"]
    assert events[-1].payload["canonical_id"] == target.id


def test_a_reject_that_clears_the_candidate_appends_an_update(db: None) -> None:
    target = run(_add("reject-target", "Lieu Cible Rejet"))
    place = run(
        _add(
            "reject",
            "Lieu Rejeté",
            duplicate_of_id=target.id,
            confidence=0.8,
            operating_status="duplicate_review",
        )
    )

    run(_review(place.id, None, None))

    events = _events(place.id)
    assert [event.op for event in events] == ["insert", "update"]
    assert events[-1].payload["duplicate_of_id"] is None


def test_a_no_change_review_state_appends_nothing(db: None) -> None:
    place = run(_add("review-noop", "Lieu Sans Changement"))

    run(_review(place.id, None, None))

    assert [event.op for event in _events(place.id)] == ["insert"]


def test_an_accepted_new_answer_appends_an_insert_event(db: None) -> None:
    place = run(_add("answer-new", "Lieu Réponse"))
    run(_upsert(place.id, {_CRITERION: {"value": True}}))

    events = _events(place.id)

    assert [event.op for event in events] == ["insert", "insert"]
    answer = events[-1]
    assert answer.entity == "place_accessibility"
    assert answer.payload["criterion_slug"] == _CRITERION
    assert answer.payload["value"] == {"value": True}


def test_overwriting_an_answer_appends_an_update_event(db: None) -> None:
    place = run(_add("answer-overwrite", "Lieu Réponse Deux"))
    run(_upsert(place.id, {_CRITERION: {"value": True}}))
    run(_upsert(place.id, {_CRITERION: {"value": False}}))

    events = _events(place.id)

    assert [event.op for event in events[-2:]] == ["insert", "update"]
    assert events[-1].payload["value"] == {"value": False}


def test_resubmitting_the_same_answer_appends_nothing(db: None) -> None:
    place = run(_add("answer-noop", "Lieu Réponse Identique"))
    observed = datetime(2026, 5, 1, 12, 0)
    run(_upsert(place.id, {_CRITERION: {"value": True}}, observed_at=observed))
    before = len(_events(place.id))

    run(_upsert(place.id, {_CRITERION: {"value": True}}, observed_at=observed))

    assert len(_events(place.id)) == before


def test_a_rejected_answer_stays_in_the_write_journal_only(db: None) -> None:
    place = run(_add("answer-rejected", "Lieu Réponse Rejetée"))
    run(_upsert(place.id, {_CRITERION: {"value": True}}, observed_at=datetime(2026, 5, 1)))
    before = len(_events(place.id))

    run(_upsert(place.id, {_CRITERION: {"value": False}}, observed_at=datetime(2026, 1, 1)))

    assert len(_events(place.id)) == before
    decision = row(
        "SELECT decision, reason FROM place_accessibility_write "
        "WHERE place_id = :place_id ORDER BY id DESC LIMIT 1",
        {"place_id": place.id},
    )
    assert (decision.decision, decision.reason) == ("rejected", "stale")


def test_reassign_category_emits_one_event_per_place_and_none_on_a_second_pass(
    db: None,
) -> None:
    category_id = scalar("SELECT id FROM categories WHERE slug = :slug", {"slug": _CATEGORY})
    first = run(_add("reassign-1", "Lieu Réaffecté Un", source_category=_UNRESOLVED))
    second = run(_add("reassign-2", "Lieu Réaffecté Deux", source_category=_UNRESOLVED))

    async def reassign() -> int:
        async with SessionLocal() as session:
            count = await SqlAlchemyPlaceRepository(session).reassign_category(
                _UNRESOLVED, category_id
            )
            await session.commit()
            return count

    assert run(reassign()) == 2
    for place in (first, second):
        events = _events(place.id)
        assert [event.op for event in events] == ["insert", "update"]
        assert events[-1].payload["category_id"] == category_id

    assert run(reassign()) == 0
    assert len(_events(first.id)) == 2


def test_duplicate_writes_journal_every_affected_place(db: None) -> None:
    target = run(_add("dedup-target", "Lieu Candidat"))
    first = run(_add("dedup-1", "Lieu En Attente Un"))
    second = run(_add("dedup-2", "Lieu En Attente Deux"))

    async def set_candidate() -> None:
        async with SessionLocal() as session:
            await SqlAlchemyPlaceRepository(session).set_duplicate_candidate(
                first.id, target.id, 0.8
            )
            await session.commit()

    run(set_candidate())
    assert [event.op for event in _events(first.id)] == ["insert", "update"]

    async def clear_candidates() -> int:
        async with SessionLocal() as session:
            count = await SqlAlchemyPlaceRepository(session).clear_duplicate_candidates()
            await session.commit()
            return count

    async def flag_second() -> None:
        async with SessionLocal() as session:
            await SqlAlchemyPlaceRepository(session).set_duplicate_candidate(
                second.id, target.id, 0.8
            )
            await session.commit()

    run(flag_second())
    assert run(clear_candidates()) >= 2
    assert [event.op for event in _events(second.id)] == ["insert", "update", "update"]
    assert _events(first.id)[-1].payload["duplicate_of_id"] is None


def test_a_rolled_back_write_leaves_no_event_and_no_place(db: None) -> None:
    async def add_then_rollback() -> int:
        async with SessionLocal() as session:
            place = await SqlAlchemyPlaceRepository(session).add(
                Place(
                    id=0,
                    name="Lieu Annulé",
                    slug=f"{_PREFIX}rollback",
                    source=_SOURCE,
                    source_id="rollback",
                )
            )
            place_id = place.id
            await session.rollback()
            return place_id

    place_id = run(add_then_rollback())

    assert scalar("SELECT id FROM place WHERE slug = :slug", {"slug": f"{_PREFIX}rollback"}) is None
    assert _events(place_id) == []

    async def add_then_commit() -> int:
        async with SessionLocal() as session:
            place = await SqlAlchemyPlaceRepository(session).add(
                Place(
                    id=0,
                    name="Lieu Validé",
                    slug=f"{_PREFIX}commit",
                    source=_SOURCE,
                    source_id="commit",
                )
            )
            await session.commit()
            return place.id

    committed = run(add_then_commit())
    assert [event.op for event in _events(committed)] == ["insert"]


def test_safe_seq_publishes_an_event_only_after_its_transaction_commits(db: None) -> None:
    async def boundary() -> tuple[int, int, int]:
        async with SessionLocal() as writer:
            place = await SqlAlchemyPlaceRepository(writer).add(
                Place(
                    id=0,
                    name="Lieu Frontière",
                    slug=f"{_PREFIX}boundary",
                    source=_SOURCE,
                    source_id="boundary",
                )
            )
            await writer.flush()
            seq = int(
                await writer.scalar(
                    select(ExportEventModel.seq).where(ExportEventModel.entity_id == place.id)
                )
            )
            async with SessionLocal() as reader:
                before = await SqlAlchemyExportEventRepository(reader).safe_seq()
            await writer.commit()
            async with SessionLocal() as reader:
                after = await SqlAlchemyExportEventRepository(reader).safe_seq()
        return seq, before, after

    seq, before, after = run(boundary())

    assert before < seq, "an in-flight transaction must not be published"
    assert after >= seq, "the committed event must be published"


def test_place_history_prints_both_events_in_seq_order(db: None) -> None:
    place = run(_add("history", "Lieu Histoire Avant"))
    run(_rename(place.id, "Lieu Histoire Après"))

    result = CliRunner().invoke(admin.app, ["place", "history", place.slug])

    assert result.exit_code == 0, result.output
    lines = result.output.strip().splitlines()
    assert len(lines) == 2
    assert "insert" in lines[0]
    assert "update" in lines[1]
    assert "name=Lieu Histoire Après" in lines[1]
