"""Functional: the ODbL export ZIP, its delta, catch-up, watermark and retention (D-10, D-15).

Runs against the real PostGIS test database: the MVCC boundary, the merged-answer remap and
the retention prune can only be proven by PostgreSQL.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from letmegetin import admin
from letmegetin.application.places import export as export_module
from letmegetin.application.places.export import ExportReport, export_odbl
from letmegetin.domain.places.entities import Place
from letmegetin.infrastructure.persistence.export_repositories import (
    SqlAlchemyExportEventRepository,
    SqlAlchemyExportRepository,
)
from letmegetin.infrastructure.persistence.repositories import SqlAlchemyPlaceRepository
from tests.db import SessionLocal, execute, require_database, rows, run, scalar

_SOURCE = "acceslibre"
_PREFIX = "cli-test-export-"
_CLOSED_LICENCE = "cli-test-export-closed"
_CLOSED_SOURCE = "cli-test-export-closed-source"
_CRITERION = f"{_PREFIX}crit"
_OTHER_CRITERION = f"{_PREFIX}crit-two"
_THIRD_CRITERION = f"{_PREFIX}crit-three"
_CATEGORY = f"{_PREFIX}category"
_OBSERVED = datetime(2026, 11, 1, 12, 0)
_PLACE_IDS = f"(SELECT id FROM place WHERE slug LIKE '{_PREFIX}%')"
_ENTRIES = {
    "places.csv",
    "categories.csv",
    "criteria.csv",
    "answers.csv",
    "aliases.csv",
    "ATTRIBUTION.txt",
    "manifest.json",
}


@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database(
        "export_event", "place", "criteria", "categories", "licence", "licence_destination"
    )
    _cleanup()
    _seed()
    yield
    _cleanup()


def _cleanup() -> None:
    # export_event has no foreign key: prune it by hand, then the place cascade clears the
    # answers, aliases and review decisions.
    execute(f"DELETE FROM export_event WHERE entity_id IN {_PLACE_IDS}")
    execute(f"DELETE FROM place WHERE slug LIKE '{_PREFIX}%'")
    execute(f"DELETE FROM criteria WHERE slug LIKE '{_PREFIX}%'")
    execute(f"DELETE FROM categories WHERE slug LIKE '{_PREFIX}%'")
    execute("DELETE FROM source_licence WHERE source LIKE :prefix", {"prefix": f"{_PREFIX}%"})
    execute(
        "DELETE FROM licence_destination WHERE licence_slug LIKE :prefix",
        {"prefix": f"{_PREFIX}%"},
    )
    execute("DELETE FROM licence WHERE slug LIKE :prefix", {"prefix": f"{_PREFIX}%"})


def _seed() -> None:
    for slug in (_CRITERION, _OTHER_CRITERION, _THIRD_CRITERION):
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
    # The reviewed matrix every export predicate reads (LIC-05).
    synced = CliRunner().invoke(admin.app, ["licences", "sync"])
    assert synced.exit_code == 0, synced.output
    # One licence the matrix keeps out of the open export, so a withheld row is provable.
    execute(
        "INSERT INTO licence (slug, name, obligations) "
        "VALUES (:slug, 'Test Closed', '[]'::jsonb) ON CONFLICT (slug) DO NOTHING",
        {"slug": _CLOSED_LICENCE},
    )
    execute(
        "INSERT INTO licence_destination (licence_slug, destination, allowed, note) "
        "VALUES (:slug, 'open_export', false, NULL) "
        "ON CONFLICT (licence_slug, destination) DO UPDATE SET allowed = false",
        {"slug": _CLOSED_LICENCE},
    )
    execute(
        "INSERT INTO source_licence (source, licence_slug, effective_from) "
        "VALUES (:source, :slug, :day) "
        "ON CONFLICT (source) DO UPDATE SET licence_slug = :slug",
        {"source": _CLOSED_SOURCE, "slug": _CLOSED_LICENCE, "day": date(2020, 1, 1)},
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
                **kwargs,  # type: ignore[arg-type]
            )
        )
        await session.commit()
        return place


async def _upsert(
    place_id: int, values: dict[str, dict[str, object]], source: str = _SOURCE
) -> None:
    async with SessionLocal() as session:
        await SqlAlchemyPlaceRepository(session).upsert_accessibility(
            place_id,
            values,
            source=source,
            actor=f"importer:{source}",
            observed_at=_OBSERVED,
        )
        await session.commit()


async def _rename(place_id: int, name: str) -> None:
    async with SessionLocal() as session:
        repository = SqlAlchemyPlaceRepository(session)
        place = await repository.get_by_id(place_id)
        assert place is not None
        place.name = name
        await repository.update(place)
        await session.commit()


async def _review(place_id: int, canonical_id: int | None) -> None:
    async with SessionLocal() as session:
        await SqlAlchemyPlaceRepository(session).set_review_state(
            place_id, canonical_id, None, "open"
        )
        await session.commit()


def _withhold_place(place_id: int) -> None:
    """Stamp the closed licence on a place directly: only the place row must be withheld."""
    execute(
        "UPDATE place SET source_license = :licence WHERE id = :place_id",
        {"licence": _CLOSED_LICENCE, "place_id": place_id},
    )


async def _export(out: Path, **kwargs: object) -> ExportReport:
    async with SessionLocal() as session:
        report = await export_odbl(
            SqlAlchemyExportRepository(session),
            SqlAlchemyExportEventRepository(session),
            out=out,
            **kwargs,  # type: ignore[arg-type]
        )
        # The CLI's runner owns the unit of work; the retention delete only lands on commit.
        await session.commit()
        return report


def _exports(out: Path, **kwargs: object) -> ExportReport:
    return run(_export(out, **kwargs))


def _csv_rows(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    text = archive.read(name).decode("utf-8")
    assert not text.startswith("\ufeff"), f"{name} must not carry a BOM"
    return list(csv.DictReader(io.StringIO(text)))


def _header(archive: zipfile.ZipFile, name: str) -> str:
    return archive.read(name).decode("utf-8").splitlines()[0]


def _latest(out: Path) -> dict[str, object]:
    return json.loads((out / "latest.json").read_text(encoding="utf-8"))


def _zip(out: Path, report: ExportReport) -> zipfile.ZipFile:
    return zipfile.ZipFile(out / report.name)


def test_snapshot_zip_carries_the_seven_files_and_only_canonical_places(
    db: None, tmp_path: Path
) -> None:
    first = run(_add("one", "Lieu Un"))
    run(_upsert(first.id, {_CRITERION: {"value": True}, _OTHER_CRITERION: {"value": True}}))
    run(_upsert(first.id, {_THIRD_CRITERION: {"value": True}}, source=_CLOSED_SOURCE))
    empty = run(_add("zero", "Lieu Sans Réponse"))
    merged = run(_add("merged", "Lieu Fusionné"))
    run(_upsert(merged.id, {_CRITERION: {"value": False}, _THIRD_CRITERION: {"value": True}}))
    run(_review(merged.id, first.id))
    withheld_place = run(_add("withheld", "Lieu Retenu"))
    run(_upsert(withheld_place.id, {_CRITERION: {"value": True}}))
    _withhold_place(withheld_place.id)

    invoked = CliRunner().invoke(admin.app, ["export", "odbl", "--out", str(tmp_path)])
    assert invoked.exit_code == 0, invoked.output
    report = next(tmp_path.glob("export-*-full.zip"))
    with zipfile.ZipFile(report) as archive:
        places = _csv_rows(archive, "places.csv")
        answers = _csv_rows(archive, "answers.csv")
        aliases = _csv_rows(archive, "aliases.csv")
        manifest = json.loads(archive.read("manifest.json"))
        attribution = archive.read("ATTRIBUTION.txt").decode("utf-8")

        assert set(archive.namelist()) == _ENTRIES

        exported_ids = {row["place_id"] for row in places}
        assert exported_ids == {str(first.id), str(empty.id)}
        assert str(merged.id) not in exported_ids
        assert str(withheld_place.id) not in exported_ids

        keyed = {(row["place_id"], row["criterion_slug"]): row["value"] for row in answers}
        assert keyed == {
            # The canonical's own answer wins over the merged one (D-04).
            (str(first.id), _CRITERION): '{"value": true}',
            (str(first.id), _OTHER_CRITERION): '{"value": true}',
            # The merged place's answer is remapped, never dropped — and the canonical's
            # withheld answer for that criterion never competed in the first place.
            (str(first.id), _THIRD_CRITERION): '{"value": true}',
        }
        assert aliases == [{"alias_id": str(merged.id), "canonical_id": str(first.id)}]

        assert manifest["excluded_answers"] == [
            {"source": _SOURCE, "licence": "lov2", "count": 1},
            {"source": _CLOSED_SOURCE, "licence": _CLOSED_LICENCE, "count": 1},
        ]
        assert manifest["place_withheld_answers"] == [
            {"source": _SOURCE, "licence": "lov2", "count": 1}
        ]
        assert manifest["excluded_places"] == [
            {"source": _SOURCE, "licence": _CLOSED_LICENCE, "count": 1}
        ]

        assert "Licence Ouverte v2.0 (Etalab 2.0)" in attribution
        assert "nom du producteur et date de dernière mise à jour" in attribution
        assert "Produced Works under the ODbL" in attribution
        assert "Later exports may include sources not listed in this one." in attribution
        assert "OpenStreetMap" not in attribution
        assert "Overture" not in attribution
        assert manifest["attribution"] == attribution
        assert manifest["attribution_ref"] == "ATTRIBUTION.txt"

    latest = _latest(tmp_path)
    assert set(latest) == {
        "schema_version",
        "generated_at",
        "referential_version",
        "snapshot",
        "watermark",
        "retention_floor_seq",
        "deltas",
        "attribution_ref",
    }
    assert latest["snapshot"] == {"name": report.name, "seq": latest["watermark"]}
    assert latest["retention_floor_seq"] == latest["watermark"]
    assert latest["deltas"] == []


def test_the_exported_plus_excluded_plus_withheld_answers_reconcile(
    db: None, tmp_path: Path
) -> None:
    first = run(_add("reconcile", "Lieu Réconcilié"))
    run(_upsert(first.id, {_CRITERION: {"value": True}}))
    run(_upsert(first.id, {_OTHER_CRITERION: {"value": True}}, source=_CLOSED_SOURCE))
    withheld_place = run(_add("reconcile-withheld", "Lieu Réconcilié Retenu"))
    run(
        _upsert(withheld_place.id, {_CRITERION: {"value": True}, _OTHER_CRITERION: {"value": True}})
    )
    _withhold_place(withheld_place.id)

    report = _exports(tmp_path)

    with _zip(tmp_path, report) as archive:
        exported = len(_csv_rows(archive, "answers.csv"))
        manifest = json.loads(archive.read("manifest.json"))
    excluded = sum(entry["count"] for entry in manifest["excluded_answers"])
    withheld = sum(entry["count"] for entry in manifest["place_withheld_answers"])
    canonical_total = scalar(
        "SELECT count(*) FROM place_accessibility a JOIN place p ON p.id = a.place_id "
        "WHERE p.slug LIKE :prefix",
        {"prefix": f"{_PREFIX}%"},
    )

    assert exported == 1
    assert (exported, excluded, withheld) == (1, 1, 2)
    assert exported + excluded + withheld == canonical_total


def test_a_delta_publishes_only_the_window_and_moves_the_watermark(
    db: None, tmp_path: Path
) -> None:
    target = run(_add("delta-target", "Lieu Cible Delta"))
    run(_upsert(target.id, {_CRITERION: {"value": True}}))
    quiet = run(_add("delta-quiet", "Lieu Silencieux"))
    run(_upsert(quiet.id, {_CRITERION: {"value": True}}))
    changed = run(_add("delta-changed", "Lieu Changé"))
    untouched = run(_add("delta-untouched", "Lieu Intact"))
    incoming = run(_add("delta-incoming", "Lieu Entrant"))

    snapshot = _exports(tmp_path)
    snapshot_header = _header(_zip(tmp_path, snapshot), "places.csv")
    before = _latest(tmp_path)

    created = run(_add("delta-new", "Lieu Nouveau"))
    run(_rename(changed.id, "Lieu Changé Après"))
    run(_upsert(incoming.id, {_OTHER_CRITERION: {"value": True}}))
    run(_review(incoming.id, target.id))

    delta = _exports(tmp_path, delta=True)

    with _zip(tmp_path, delta) as archive:
        places = _csv_rows(archive, "places.csv")
        answers = _csv_rows(archive, "answers.csv")
        aliases = _csv_rows(archive, "aliases.csv")
        manifest = json.loads(archive.read("manifest.json"))

        # (a) only rows whose event fell in (watermark, safe_seq()]; a changed place carries
        # its NEW value and a place untouched since before the watermark is absent.
        assert {row["place_id"] for row in places} == {str(created.id), str(changed.id)}
        assert {row["name"] for row in places} == {"Lieu Nouveau", "Lieu Changé Après"}
        assert str(untouched.id) not in {row["place_id"] for row in places}

        # (b) the merged place appears only in aliases.csv.
        assert aliases == [{"alias_id": str(incoming.id), "canonical_id": str(target.id)}]
        assert str(incoming.id) not in {row["place_id"] for row in places}

        # (c) the same schema as the snapshot.
        assert _header(archive, "places.csv") == snapshot_header

        # (e) an answer changed in the window arrives under its canonical id, and a merge
        # re-emits the winners of the place it merged into (the deliberate superset of B7).
        keyed = {(row["place_id"], row["criterion_slug"]) for row in answers}
        assert keyed == {
            (str(target.id), _CRITERION),
            (str(target.id), _OTHER_CRITERION),
        }
        # A winner whose inputs did not move, and whose place saw no merge, is absent.
        assert (str(quiet.id), _CRITERION) not in keyed

        # (W5) the manifest announces the window it ships.
        assert (manifest["mode"], manifest["from_seq"], manifest["to_seq"]) == (
            "delta",
            before["watermark"],
            delta.watermark,
        )

    after = _latest(tmp_path)
    # (d) the snapshot is unchanged, the watermark moved and the delta is listed.
    assert after["snapshot"] == before["snapshot"]
    assert after["watermark"] == delta.watermark > before["watermark"]
    assert after["deltas"] == [
        {"name": delta.name, "from_seq": before["watermark"], "to_seq": delta.watermark}
    ]
    assert (tmp_path / snapshot.name).exists()


def test_a_merge_in_the_window_re_emits_its_winners_even_without_an_answer_event(
    db: None, tmp_path: Path
) -> None:
    canonical = run(_add("merge-canonical", "Lieu Canonique"))
    run(_upsert(canonical.id, {_CRITERION: {"value": True}}))
    incoming = run(_add("merge-incoming", "Lieu Sans Réponse"))
    snapshot = _exports(tmp_path)

    run(_review(incoming.id, canonical.id))

    delta = _exports(tmp_path, delta=True)

    with _zip(tmp_path, delta) as archive:
        answers = _csv_rows(archive, "answers.csv")
        assert {(row["place_id"], row["criterion_slug"]) for row in answers} == {
            (str(canonical.id), _CRITERION)
        }
    assert delta.watermark > snapshot.watermark


def test_a_failed_delta_leaves_the_watermark_untouched(
    db: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run(_add("watermark-one", "Lieu Avant Échec"))
    _exports(tmp_path)
    run(_add("watermark-two", "Lieu Après Échec"))
    before = _latest(tmp_path)

    def _explode(*args: object, **kwargs: object) -> int:
        raise RuntimeError("disk full")

    monkeypatch.setattr(export_module, "_write_csv_entry", _explode)
    failed = CliRunner().invoke(admin.app, ["export", "odbl", "--out", str(tmp_path), "--delta"])

    assert failed.exit_code != 0
    assert _latest(tmp_path) == before
    assert not list(tmp_path.glob("delta-*.zip"))


def test_a_catch_up_replays_since_the_snapshot_and_refuses_below_the_floor(
    db: None, tmp_path: Path
) -> None:
    kept = run(_add("catchup-kept", "Lieu Conservé"))
    snapshot = _exports(tmp_path)
    before = (tmp_path / "latest.json").read_bytes()
    created = run(_add("catchup-new", "Lieu Depuis"))
    run(_rename(kept.id, "Lieu Conservé Après"))
    incoming = run(_add("catchup-merged", "Lieu Fusionné Depuis"))
    run(_review(incoming.id, kept.id))

    catch_up = _exports(tmp_path, since=snapshot.snapshot_seq)

    with _zip(tmp_path, catch_up) as archive:
        places = _csv_rows(archive, "places.csv")
        aliases = _csv_rows(archive, "aliases.csv")
        assert {row["place_id"] for row in places} == {str(kept.id), str(created.id)}
        assert aliases == [{"alias_id": str(incoming.id), "canonical_id": str(kept.id)}]
    assert (tmp_path / "latest.json").read_bytes() == before

    refused = CliRunner().invoke(
        admin.app,
        ["export", "odbl", "--out", str(tmp_path), "--since", str(snapshot.snapshot_seq - 1)],
    )
    assert refused.exit_code == 1
    assert "retention floor" in refused.output
    assert snapshot.name in refused.output


def test_a_delta_never_skips_an_event_from_an_in_flight_transaction(
    db: None, tmp_path: Path
) -> None:
    _exports(tmp_path)

    async def scenario() -> tuple[Place, ExportReport, ExportReport]:
        async with SessionLocal() as holding:
            place = await SqlAlchemyPlaceRepository(holding).add(
                Place(
                    id=0,
                    name="Lieu En Vol",
                    slug=f"{_PREFIX}in-flight",
                    source=_SOURCE,
                    source_id="in-flight",
                )
            )
            await holding.flush()
            first = await _export(tmp_path, delta=True)
            await holding.commit()
        second = await _export(tmp_path, delta=True)
        return place, first, second

    place, first, second = run(scenario())

    assert str(place.id) not in {
        row["place_id"] for row in _csv_rows(_zip(tmp_path, first), "places.csv")
    }
    assert str(place.id) in {
        row["place_id"] for row in _csv_rows(_zip(tmp_path, second), "places.csv")
    }
    assert second.watermark > first.watermark


def test_retention_prunes_to_the_previous_snapshot_and_removes_old_deltas(
    db: None, tmp_path: Path
) -> None:
    run(_add("retention-first", "Lieu Cycle Un"))
    first_snapshot = _exports(tmp_path)
    first_boundary = first_snapshot.snapshot_seq

    run(_add("retention-second", "Lieu Cycle Deux"))
    delta = _exports(tmp_path, delta=True)
    orphan = tmp_path / "delta-20200101T000000Z.zip"
    orphan.write_bytes(b"orphan")

    second_snapshot = _exports(tmp_path)

    assert second_snapshot.retention_floor_seq == first_boundary
    # (a) every event up to the FIRST snapshot boundary is gone.
    assert (
        scalar(
            "SELECT count(*) FROM export_event WHERE seq <= :boundary",
            {"boundary": first_boundary},
        )
        == 0
    )
    # ... while the events the two most recent cycles wrote survive.
    surviving = rows(
        "SELECT seq, entity_id FROM export_event "
        "WHERE entity_id IN (SELECT id FROM place WHERE slug LIKE :prefix)",
        {"prefix": f"{_PREFIX}%"},
    )
    assert surviving
    assert all(event.seq > first_boundary for event in surviving)
    assert second_snapshot.pruned_events > 0
    # (c) the delta the new snapshot subsumes is gone, the snapshot ZIPs are not (B3).
    assert not (tmp_path / delta.name).exists()
    assert (tmp_path / first_snapshot.name).exists()
    assert (tmp_path / second_snapshot.name).exists()
    # (d) an orphan delta ZIP nobody listed is removed (I4).
    assert not orphan.exists()


def test_a_failed_snapshot_prunes_nothing(
    db: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run(_add("failed-first", "Lieu Cycle Un"))
    first_snapshot = _exports(tmp_path)
    run(_add("failed-second", "Lieu Cycle Deux"))
    before = scalar("SELECT count(*) FROM export_event")

    def _explode(*args: object, **kwargs: object) -> int:
        raise RuntimeError("disk full")

    monkeypatch.setattr(export_module, "_write_csv_entry", _explode)
    with pytest.raises(RuntimeError):
        _exports(tmp_path)

    assert scalar("SELECT count(*) FROM export_event") == before
    assert (tmp_path / first_snapshot.name).exists()
    assert not list(tmp_path.glob("export-*-full.zip.tmp"))
    assert not list(tmp_path.glob(".export-*.zip.tmp"))
