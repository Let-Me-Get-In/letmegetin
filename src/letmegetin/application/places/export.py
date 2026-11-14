"""Assemble the ODbL export: a full snapshot, a moving-watermark delta or a catch-up (D-10).

The boundary (``safe_seq()``) and every streamed row are read inside ONE REPEATABLE READ
transaction, so a delta can never skip or double-count an event (B5, B6). The watermark in
``latest.json`` advances only after the delta ZIP is written and fsynced (D-10), and retention
runs last, inside the same ``flock``, once the snapshot that replaces the old boundary is on
disk (D-15).

Dates are source-first: ``observed_at`` else ``retrieved_at`` for a place, ``observed_at``
else ``recorded_at`` for an answer — an answer has no ``retrieved_at`` (D-06, I2).
"""

from __future__ import annotations

import csv
import fcntl
import io
import json
import os
import zipfile
from collections.abc import AsyncIterator, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from pathlib import Path

from letmegetin.application.places.attribution import (
    FORWARD_LOOKING_SENTENCE,
    PRODUCED_WORKS_SENTENCE,
    render_source_line,
)
from letmegetin.application.referential.licences import load_licences
from letmegetin.config import settings
from letmegetin.core.exceptions import DomainError
from letmegetin.domain.places.export import ExportEventRepository
from letmegetin.domain.places.export_plan import (
    ALIASES_FILE,
    ALIASES_HEADER,
    ANSWERS_FILE,
    ANSWERS_HEADER,
    ATTRIBUTION_FILE,
    CATEGORIES_FILE,
    CATEGORIES_HEADER,
    CRITERIA_FILE,
    CRITERIA_HEADER,
    MANIFEST_FILE,
    MODE_SNAPSHOT,
    PLACES_FILE,
    PLACES_HEADER,
    SCHEMA_VERSION,
    AnswerRow,
    ExportPlanRepository,
    ExportRow,
    PlaceRow,
    build_manifest,
    guard_indexes,
    guarded_cells,
)
from letmegetin.domain.referential.entities import Licence

DESTINATION = "open_export"
MODE_DELTA = "delta"
MODE_SINCE = "since"

Counts = list[tuple[str, str | None, int]]


@dataclass
class ExportReport:
    """What one ``export odbl`` run did, for the CLI to print."""

    name: str
    mode: str
    files: dict[str, int]
    excluded_places: Counts
    excluded_answers: Counts
    place_withheld_answers: Counts
    snapshot_seq: int
    watermark: int
    retention_floor_seq: int
    pruned_events: int = 0
    pruned_deltas: list[str] = field(default_factory=list)


@dataclass
class _ZipResult:
    files: dict[str, int]
    attribution: str
    manifest: dict[str, object]
    excluded_places: Counts
    excluded_answers: Counts
    place_withheld_answers: Counts


@dataclass
class _Presence:
    """The sources this ZIP actually exports, with the newest date each one carries (D-05)."""

    latest: dict[tuple[str, str | None], datetime | None] = field(default_factory=dict)

    def see(self, source: str, licence: str | None, moment: datetime | None) -> None:
        key = (source, licence)
        current = self.latest.get(key)
        fresher = moment is not None and (current is None or moment > current)
        if key not in self.latest or fresher:
            self.latest[key] = moment


def _read_latest(out: Path) -> dict[str, object] | None:
    path = out / "latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DomainError(f"{path} is unreadable: {exc}") from exc


def _int_field(latest: Mapping[str, object], key: str) -> int:
    value = latest.get(key)
    if not isinstance(value, int):
        raise DomainError(f"latest.json carries no integer '{key}'")
    return value


def _snapshot_of(latest: Mapping[str, object]) -> tuple[str, int] | None:
    snapshot = latest.get("snapshot")
    if not isinstance(snapshot, dict):
        return None
    name = snapshot.get("name")
    seq = snapshot.get("seq")
    if not isinstance(name, str) or not isinstance(seq, int):
        raise DomainError("latest.json snapshot needs a name and a seq")
    return name, seq


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_dir(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_atomic(path: Path, payload: bytes) -> None:
    """temp file + fsync + ``os.replace``: a reader never sees a half-written latest.json."""
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_dir(path.parent)


@contextmanager
def _export_lock(out: Path) -> Iterator[None]:
    """One generator at a time: the reader of latest.json also owns its rewrite (W-CONCURRENCY)."""
    out.mkdir(parents=True, exist_ok=True)
    with (out / "latest.json.lock").open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


async def _aiter[T](rows: Iterable[T]) -> AsyncIterator[T]:
    for row in rows:
        yield row


async def _seeing[T: PlaceRow | AnswerRow](
    rows: AsyncIterator[T], presence: _Presence
) -> AsyncIterator[T]:
    async for row in rows:
        presence.see(row.source, row.source_license, row.date)
        yield row


async def _write_csv_entry(
    archive: zipfile.ZipFile,
    name: str,
    header: tuple[str, ...],
    file: str,
    rows: AsyncIterator[ExportRow],
) -> int:
    """Stream one CSV entry; returns its data row count (header excluded)."""
    indexes = guard_indexes(header, file)
    raw = archive.open(name, "w", force_zip64=True)
    sink = io.TextIOWrapper(raw, encoding="utf-8", newline="")
    writer = csv.writer(sink, lineterminator="\n")
    count = 0
    try:
        writer.writerow(list(header))
        async for row in rows:
            writer.writerow(guarded_cells(row, indexes))
            count += 1
        sink.flush()
    finally:
        # Closing the text wrapper closes the ZIP entry, which is what finalises it.
        sink.close()
    return count


def _licence_catalogue() -> dict[str, Licence]:
    """Legal names and the reviewed sentence come from the CSV, never from code (D-05)."""
    return {licence.slug: licence for licence in load_licences(settings.data_dir / "licences.csv")}


def _render_attribution(presence: _Presence, licences: Mapping[str, Licence]) -> str:
    lines: list[str] = []
    for (source, licence), moment in sorted(
        presence.latest.items(), key=lambda item: (item[0][0], item[0][1] or "")
    ):
        known = licences.get(licence or "")
        lines.append(
            render_source_line(
                source,
                known.name if known else (licence or "unknown licence"),
                moment.date() if moment else None,
                known.attribution_text if known else None,
            )
        )
    lines.extend([PRODUCED_WORKS_SENTENCE, FORWARD_LOOKING_SENTENCE])
    return "\n".join(lines) + "\n"


async def _write_zip(
    archive_path: Path,
    export: ExportPlanRepository,
    *,
    generated_at: datetime,
    mode: str,
    boundary: int,
    from_seq: int | None,
    answer_window: tuple[int, int] | None,
) -> _ZipResult:
    """Stream the seven entries; ATTRIBUTION and the manifest close the archive."""
    presence = _Presence()
    files: dict[str, int] = {}
    temporary = archive_path.with_name(f".{archive_path.name}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            files[PLACES_FILE] = await _write_csv_entry(
                archive,
                PLACES_FILE,
                PLACES_HEADER,
                PLACES_FILE,
                _seeing(export.stream_canonical_places(DESTINATION, from_seq), presence),
            )
            files[CATEGORIES_FILE] = await _write_csv_entry(
                archive,
                CATEGORIES_FILE,
                CATEGORIES_HEADER,
                CATEGORIES_FILE,
                _aiter(await export.list_categories()),
            )
            files[CRITERIA_FILE] = await _write_csv_entry(
                archive,
                CRITERIA_FILE,
                CRITERIA_HEADER,
                CRITERIA_FILE,
                _aiter(await export.list_criteria()),
            )
            files[ANSWERS_FILE] = await _write_csv_entry(
                archive,
                ANSWERS_FILE,
                ANSWERS_HEADER,
                ANSWERS_FILE,
                _seeing(export.stream_answers(DESTINATION, answer_window), presence),
            )
            files[ALIASES_FILE] = await _write_csv_entry(
                archive,
                ALIASES_FILE,
                ALIASES_HEADER,
                ALIASES_FILE,
                export.stream_aliases(from_seq),
            )
            excluded_places = await export.place_exclusion_counts(DESTINATION)
            excluded_answers = await export.answer_exclusion_counts(DESTINATION)
            withheld_answers = await export.place_withheld_answer_counts(DESTINATION)
            attribution = _render_attribution(presence, _licence_catalogue())
            archive.writestr(ATTRIBUTION_FILE, attribution)
            files[ATTRIBUTION_FILE] = 1
            files[MANIFEST_FILE] = 1
            manifest = build_manifest(
                generated_at=generated_at,
                referential_version=await export.referential_version(),
                files=files,
                excluded_places=excluded_places,
                excluded_answers=excluded_answers,
                place_withheld_answers=withheld_answers,
                attribution=attribution,
                mode=mode,
                from_seq=from_seq,
                to_seq=boundary,
            )
            archive.writestr(
                MANIFEST_FILE, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
            )
        _fsync_file(temporary)
        os.replace(temporary, archive_path)
        _fsync_dir(archive_path.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return _ZipResult(
        files=files,
        attribution=attribution,
        manifest=manifest,
        excluded_places=excluded_places,
        excluded_answers=excluded_answers,
        place_withheld_answers=withheld_answers,
    )


def _prune_deltas(out: Path, listed: set[str]) -> list[str]:
    """Remove delta ZIPs a fresh snapshot made meaningless, plus unlisted orphans (D-15, I4).

    A snapshot sequence is a later ``safe_seq()`` than every delta's ``to_seq``, so the
    "subsumed" rule and the "orphan" rule collapse into one: keep only what latest.json lists.
    """
    pruned: list[str] = []
    for path in sorted(out.glob("delta-*.zip")):
        if path.name in listed:
            continue
        path.unlink(missing_ok=True)
        pruned.append(path.name)
    return pruned


async def export_odbl(
    export: ExportPlanRepository,
    events: ExportEventRepository,
    *,
    out: Path,
    since: int | None = None,
    since_date: date | None = None,
    delta: bool = False,
) -> ExportReport:
    """Write one ZIP plus ``latest.json``; a snapshot also prunes the journal (D-10, D-15)."""
    if delta and (since is not None or since_date is not None):
        raise DomainError("--delta and --since are exclusive: a delta follows the watermark")
    if since is not None and since_date is not None:
        raise DomainError("--since takes a sequence number or an ISO date, not both")
    mode = (
        MODE_DELTA if delta else (MODE_SINCE if since is not None or since_date else MODE_SNAPSHOT)
    )
    out = out.expanduser()
    with _export_lock(out):
        latest = _read_latest(out)
        if delta and latest is None:
            raise DomainError(f"no latest.json in {out}: run a full snapshot before a delta")
        previous = _snapshot_of(latest) if latest is not None else None
        stored_watermark = _int_field(latest, "watermark") if latest is not None else 0
        floor = _int_field(latest, "retention_floor_seq") if latest is not None else 0

        # First statement of the REPEATABLE READ transaction: it pins the snapshot that every
        # later read, and the boundary itself, then share (B5).
        await export.begin_repeatable_read()
        boundary = await events.safe_seq()

        from_seq: int | None = None
        if delta:
            from_seq = stored_watermark
        elif since is not None:
            from_seq = since
        elif since_date is not None:
            from_seq = await events.seq_at_or_before(datetime.combine(since_date, time.max))

        if mode == MODE_SINCE and from_seq is not None and from_seq < floor:
            name, seq = previous or ("(none)", 0)
            raise DomainError(
                f"--since {from_seq} is below the retention floor {floor}: the journal before "
                f"it was pruned. Restart from the snapshot '{name}' (seq {seq})."
            )

        generated_at = datetime.now(UTC)
        # Microseconds keep two runs in the same second from overwriting each other's ZIP.
        stamp = generated_at.strftime("%Y%m%dT%H%M%S%fZ")
        name = {
            MODE_SNAPSHOT: f"export-{stamp}-full.zip",
            MODE_DELTA: f"delta-{stamp}.zip",
            MODE_SINCE: f"export-{stamp}-since-{from_seq}.zip",
        }[mode]
        result = await _write_zip(
            out / name,
            export,
            generated_at=generated_at,
            mode=mode,
            boundary=boundary,
            from_seq=from_seq,
            answer_window=None if from_seq is None else (from_seq, boundary),
        )

        deltas: list[dict[str, object]] = []
        summary: dict[str, object] | None = None
        retention_floor = floor
        if mode == MODE_SNAPSHOT:
            # The old snapshot boundary becomes the floor: events below it are pruned, so a
            # replay from either of the last two snapshots stays possible (D-15).
            retention_floor = previous[1] if previous is not None else boundary
            summary = {
                "schema_version": SCHEMA_VERSION,
                "generated_at": result.manifest["generated_at"],
                "referential_version": result.manifest["referential_version"],
                "snapshot": {"name": name, "seq": boundary},
                "watermark": boundary,
                "retention_floor_seq": retention_floor,
                "deltas": deltas,
                "attribution_ref": ATTRIBUTION_FILE,
            }
        elif mode == MODE_DELTA:
            summary = dict(latest or {})
            raw_deltas = summary.get("deltas")
            if isinstance(raw_deltas, list):
                deltas = [entry for entry in raw_deltas if isinstance(entry, dict)]
            deltas.append({"name": name, "from_seq": from_seq, "to_seq": boundary})
            summary.update(
                {
                    "schema_version": SCHEMA_VERSION,
                    "generated_at": result.manifest["generated_at"],
                    "referential_version": result.manifest["referential_version"],
                    "watermark": boundary,
                    "deltas": deltas,
                    "attribution_ref": ATTRIBUTION_FILE,
                }
            )

        if summary is not None:
            # The ZIP is written and fsynced above; only now may the watermark move (D-10).
            _write_atomic(
                out / "latest.json",
                json.dumps(summary, ensure_ascii=False, indent=2).encode() + b"\n",
            )

        pruned_events = 0
        pruned_deltas: list[str] = []
        if mode == MODE_SNAPSHOT:
            if previous is not None:
                pruned_events = await events.delete_up_to(previous[1])
            pruned_deltas = _prune_deltas(out, {str(entry.get("name")) for entry in deltas})

        last_snapshot = boundary if mode == MODE_SNAPSHOT else (previous or (name, boundary))[1]

    return ExportReport(
        name=name,
        mode=mode,
        files=result.files,
        excluded_places=result.excluded_places,
        excluded_answers=result.excluded_answers,
        place_withheld_answers=result.place_withheld_answers,
        snapshot_seq=last_snapshot,
        watermark=boundary if mode in {MODE_SNAPSHOT, MODE_DELTA} else stored_watermark,
        retention_floor_seq=retention_floor,
        pruned_events=pruned_events,
        pruned_deltas=pruned_deltas,
    )
