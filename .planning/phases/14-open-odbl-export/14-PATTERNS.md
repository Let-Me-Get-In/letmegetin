# Phase 14: Open ODbL export - Pattern Map

**Mapped:** 2026-11-14
**Files analyzed:** 18 (create + modify)
**Analogs found:** 16 / 18

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/letmegetin/domain/places/export.py` (event entity + ports) | domain (pure) | transform | `domain/places/entities.py` + `domain/places/repositories.py` | exact |
| `src/letmegetin/domain/places/repositories.py` (extend) | port | — | itself (`CoverageRepository` read-only port, lines 189–194) | exact |
| `src/letmegetin/infrastructure/persistence/models.py` (extend) | model | — | itself (`PlaceAccessibilityWriteModel` lines 323–347) | exact |
| `migrations/versions/0012_export_event.py` | migration | — | `migrations/versions/0011_licence_provenance.py` | exact |
| `src/letmegetin/infrastructure/persistence/export_repositories.py` (new) | repository | CRUD | `licence_repositories.py` + `repositories.py` `SqlAlchemyPlaceRepository` | role-match |
| `src/letmegetin/application/places/export.py` (new) | service (use case) | batch/transform | `application/places/coverage.py` | role-match |
| `src/letmegetin/application/places/history.py` (new) | service (use case) | transform | `application/places/duplicates.py` (`list_pending`) | role-match |
| `src/letmegetin/admin.py` (extend: `export`, `place history`) | CLI (Typer) | batch | itself (`coverage` lines 865–887, `retention` 1008–1021) | exact |
| `src/letmegetin/api/v1/export.py` (new) | controller | request-response | `api/v1/referential.py` (ETag/Response) + `api/deps.py` rate limit | role-match |
| `src/letmegetin/api/v1/router.py` (extend) | router | — | itself (lines 9–12) | exact |
| `src/letmegetin/config.py` (extend: `export_dir`) | config | — | itself (`data_dir` line 19) | exact |
| `scripts/export-odbl.sh` (new) | ops script | file-I/O | `scripts/backup.sh` + `scripts/with-secrets.sh` | role-match |
| `deploy/systemd/letmegetin-export-odbl.{service,timer}` (new) | ops | — | `deploy/systemd/letmegetin-retention.{service,timer}` | exact |
| `docs/public-api.md` (extend) | doc | — | itself (endpoints table lines 39–50, "Versioning and licence" line 173) | exact |
| `docs/openapi.json` (regenerate) | generated | — | `scripts/export_openapi.py` | exact |
| `tests/unit/application/places/test_export.py` (new) | test | — | `tests/unit/application/places/test_duplicates.py` | exact |
| `tests/functional/places/test_export.py` (new) | test | — | `tests/functional/referential/test_admin_cli.py` | exact |
| `tests/integration/api/test_openapi.py` (extend) | test | — | itself (lines 9–20) | exact |

> All analogs are git-tracked source under `src/`, `migrations/`, `tests/`, `scripts/`, `deploy/`, `docs/`. No `.gsd` capability mirrors exist in this repo.

---

## Pattern Assignments

### 1. `src/letmegetin/domain/places/export.py` (domain, transform) — NEW

The `export_event` entity and the export read/write ports. Two concerns: the append-only
journal (an entity + a `Protocol` port) and the bulk-extraction read (a read-only port).

**Analog — append-only journal entity:** `domain/places/entities.py` `ReviewDecision`
(lines 139–148) — the exact frozen-dataclass-with-actor pattern for an audit row:

```python
@dataclass
class ReviewDecision:
    place_id: int
    candidate_id: int | None
    score: float
    decision: Literal["merge", "reject"]
    actor: str = "operator"
    note: str | None = None
```

The `ExportEvent` dataclass mirrors it (D-07): `seq: int`, `occurred_at: datetime`,
`entity: Literal["place", "place_accessibility"]`, `entity_id: int`, `op: Literal["insert", "update", "merge"]`,
`actor: str`, `payload: dict` (complete post-write row state).

**Analog — read-only port:** `domain/places/repositories.py` `CoverageRepository`
(lines 189–194), the precedent for a dedicated read-only aggregate port:

```python
class CoverageRepository(Protocol):
    """Aggregate counts for the coverage export (read-only, safe on production)."""
    async def by_category_country(self) -> list[tuple[str, str, int, int]]: ...
```

The new `ExportRepository` / `ExportEventRepository` ports follow this shape: methods to
stream canonical places, stream answers, stream aliases, list categories/criteria, and
append/list events. The planner must decide port method signatures — no existing port
method returns the raw `criterion_id` needed to key `answers.csv` (see Gap 1).

---

### 2. `src/letmegetin/domain/places/repositories.py` (port) — MODIFY

Adds the export ports. `PlaceRepository` already carries the write choke points the events
hook into: `add` (line 72), `update` (line 74), `upsert_accessibility` (lines 121–141),
`set_review_state` (lines 48–56, the merge path). No read method today lists *all* places
or *all* answers for bulk export — `list_near` (76–95) is spatial, `list_accessibility`
(109) is single-place. `list_accessibility_for_places` (111–119) is the closest bulk read
and the shape to extend for the export's answer stream.

---

### 3. `src/letmegetin/infrastructure/persistence/models.py` (model) — MODIFY

Adds `ExportEventModel`. **Analog:** `PlaceAccessibilityWriteModel` (lines 323–347) — the
established append-only journal shape, including its `CheckConstraint` pattern:

```python
class PlaceAccessibilityWriteModel(Base):
    __tablename__ = "place_accessibility_write"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('accepted','rejected')", name="place_accessibility_write_decision_ck"
        ),
        ...
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    ...
    value: Mapped[dict] = mapped_column(JSONB, default=dict)
    actor: Mapped[str] = mapped_column(String(64))
    created: Mapped[datetime] = mapped_column(server_default=func.now())
```

`ExportEventModel` mirrors it: `seq` (monotone — use `BigInteger` + `Identity` or a
`Sequence`; D-07 requires monotone, unlike `place_accessibility_write.id` which is only
per-row), `occurred_at`, `entity`, `entity_id`, `op`, `actor`, `payload` (JSONB). The
`entity`/`op` enums get `CheckConstraint`s exactly like `decision`/`reason` above. Note
`ReferentialVersionModel` (lines 450–456) is the single-row version analog, not needed here.

---

### 4. `migrations/versions/0012_export_event.py` (migration) — NEW

**Analog:** `migrations/versions/0011_licence_provenance.py` — the most recent migration;
copy its `op.create_table` + `CheckConstraint` + `create_index` structure. The
`place_accessibility_write` table block (lines 142–171) is the template for the new table:

```python
op.create_table(
    "place_accessibility_write",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    ...
    sa.Column("value", _JSONB, nullable=False),
    sa.Column("decision", sa.String(length=16), nullable=False),
    ...
    sa.CheckConstraint(
        "decision IN ('accepted','rejected')",
        name="place_accessibility_write_decision_ck",
    ),
    sa.PrimaryKeyConstraint("id"),
)
op.create_index("ix_place_accessibility_write_place_id", "place_accessibility_write", ["place_id"], unique=False)
```

`_JSONB = postgresql.JSONB(astext_type=sa.Text())` (line 23) is the JSONB column helper.
`down_revision` becomes `"0011"`. No backfill is needed — D-09 says the journal starts
empty at the first export (unlike 0011's `_backfill`); the `upgrade()` here is a pure
`create_table`.

---

### 5. `src/letmegetin/infrastructure/persistence/export_repositories.py` (repository) — NEW

Two halves: the event writer (append in the same transaction as the write) and the bulk
read (extraction for the CSV/ZIP).

**Analog — writer:** `repositories.py` `add_contribution` (lines 1105–1126) shows the
flush-based append inside an existing session (no commit — caller owns the unit of work):

```python
async def add_contribution(self, place_id, user_id, criterion_id, value) -> None:
    self._session.add(
        ContributionModel(place_id=place_id, user_id=user_id, criterion_id=criterion_id, value=value)
    )
    await self._session.flush()
```

The event writers call `self._session.add(ExportEventModel(...))` + `flush()` at the same
choke points. **Critical integration:** the writes are in `SqlAlchemyPlaceRepository`
(`add` 750–778, `update` 780–806, `set_review_state` 703–717, `upsert_accessibility`
942–1034) — the planner must decide whether the event append lives *inside* those methods
or in the application use cases (`import_acceslibre._import_row`, `contribute.contribute`,
`duplicates.merge_duplicate`) that already hold the repository set. D-08 says "same
transaction as the write", which both satisfy; the choke-point wording in D-08 ("the
existing single choke points") favours appending at the repository method so no caller can
forget.

**Analog — bulk read:** `licence_repositories.py` `redistributable_place_ids` (159–177)
and `exclusion_counts` (179–188) — the SQL pushed-down extraction pattern, streaming-safe
`select(...).where(...)` with no materialisation:

```python
async def redistributable_place_ids(self, destination: str) -> list[int]:
    statement = (
        select(PlaceModel.id)
        .join(LicenceDestinationModel, and_(
            LicenceDestinationModel.licence_slug == PlaceModel.source_license,
            LicenceDestinationModel.destination == destination,
            LicenceDestinationModel.allowed.is_(True),
        ))
        .order_by(PlaceModel.id)
    )
    return list((await self._session.scalars(statement)).all())
```

The export read must filter `PlaceModel.canonical_id.is_(None)` (D-04) — see
`list_for_dedup` (line 636) and `SqlAlchemyCoverageRepository.by_category_country`
(line 1223) for the canonical-only `where` clause.

---

### 6. `src/letmegetin/application/places/export.py` (use case, batch/transform) — NEW

The `export odbl` use case: read rows, filter by licence, write CSV + ZIP + manifest.

**Analog:** `application/places/coverage.py` — the CSV emission is the one pure-stdlib
analog for writing CSV text without string concatenation (lines 63–72):

```python
import csv
import io

def coverage_csv(rows: Iterable[CoverageRow]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COVERAGE_HEADER)
    for row in rows:
        writer.writerow([row.category, row.country, row.places, row.with_accessibility, row.fill_rate])
    return buffer.getvalue()
```

D-02 mandates `csv.writer` (RFC 4180 quoting), UTF-8, header row, no BOM — exactly this
pattern, per-file. **No ZIP analog exists in `src/`** (see Gap 2): the ZIP assembly uses
stdlib `zipfile` + `io.BytesIO`, with `import_acceslibre.iter_acceslibre_rows` (173–197)
as the streaming precedent (the export is 635k places / 1.7M answers — stream row-by-row,
never materialise a list, mirroring the importer's iterator contract and the
`_progress` wrapper in `admin.py` 662–668).

**Filtering:** call `can_redistribute` / `redistributable_place_ids` rather than
re-implement the matrix (CONTEXT "Reusable Assets"). The `ATTRIBUTION.txt` + `manifest.json`
text is built from `data/referential/source_licences.csv` + `licence_destinations.csv`
(reviewed data, LIC-05), not hard-coded — mirror `licences.py` `sync_licences` loading.

---

### 7. `src/letmegetin/application/places/history.py` (use case, transform) — NEW

`place history <slug>`: read events for a place, diff consecutive full-row payloads.

**Analog:** `application/places/duplicates.py` `list_pending` (lines 32–42) — the
"repository → sorted list → report" use-case shape. The changed-field summary is computed
at read time (D-13) by diffing `payload` of consecutive events by `seq`; the diff logic is
pure and belongs here (or in `domain/places/export.py`), not in the repository.

---

### 8. `src/letmegetin/admin.py` (CLI) — MODIFY

Adds `export_app = typer.Typer(...)` + `app.add_typer(export_app, name="export")` and a
`place_app` for `place history` (or a top-level `place` command).

**Analog — sub-command registration:** the `licences_app` / `import_app` block
(lines 107–121) shows the typer-app pattern; `duplicates_app` (108) is the closest in
shape to a new `place_app`:

```python
import_app = typer.Typer(help="Import open place datasets (Acceslibre first).")
app.add_typer(import_app, name="import")
```

**Analog — `--out` / `--format csv`:** the `coverage` command (lines 865–887) is the
exact existing pattern for writing a CSV to `--out`:

```python
@app.command("coverage")
def coverage_export(
    fmt: Annotated[Literal["table", "csv"], typer.Option("--format", help="table or csv")] = "table",
    out: Annotated[Path | None, typer.Option("--out", help="Write the CSV to this file")] = None,
) -> None:
    ...
    payload = coverage_csv(rows)
    if out is None:
        return payload.rstrip("\n")
    out.write_text(payload, encoding="utf-8")
    return f"coverage csv: {len(rows) - 1} rows -> {out}"
```

`export odbl --out <dir> [--since ...]` uses the same `--out` + write-to-disk shape, but
`--out` is a *directory* (multiple CSV + manifest + ZIP). The `_run_admin(callback,
bump=False)` runner (lines 129–157) wraps it; **`bump=False` is mandatory** — an export is
read-only and must not rebuild grids. `--since <seq|date>` is the only new flag; the
`retention` command (1008–1021) shows a `--dry-run` flag analog if one is wanted.

---

### 9. `src/letmegetin/api/v1/export.py` (controller, request-response) — NEW

Two read-only routes: `GET /api/v1/export/latest.json` and
`GET /api/v1/export/{name}.zip`, both under the existing anonymous rate limit.

**Analog — rate-limited read router:** `api/v1/referential.py` lines 30–32 set the router
prefix + rate-limit dependency:

```python
router = APIRouter(
    prefix="/api/v1", tags=["referential"], dependencies=[Depends(public_rate_limit)]
)
```

**Analog — `Response` + headers:** `get_category_grid` (referential.py 84–108) shows the
`Response`/`JSONResponse` + `ETag` + `Cache-Control` pattern; a static ZIP would set
`Cache-Control: public, max-age=...` but *not* `304` (files are immutable per generation).
`latest.json` is a tiny JSON `Response`.

**No `StaticFiles`/`FileResponse` analog exists anywhere in `src/`** (grep confirms zero
hits — see Gap 3). The planner must introduce `from fastapi.responses import FileResponse`
and serve `{name}.zip` by path, or mount `StaticFiles`. `FileResponse` is the smaller,
lazy choice: one route, path-traversal guarded (reject `..`), matching D-11 "read-only
through `/api/v1/export/{name}.zip`". The `export_dir` (config) must be mounted/read by
the API process in prod — same volume as the host timer writes (D-12).

---

### 10. `src/letmegetin/api/v1/router.py` (router) — MODIFY

One line added to the aggregation (lines 7–12):

```python
from letmegetin.api.v1 import auth, export, places, referential
router = APIRouter()
router.include_router(auth.router)
router.include_router(referential.router)
router.include_router(places.router)
router.include_router(export.router)
```

---

### 11. `src/letmegetin/config.py` (config) — MODIFY

Adds `export_dir: Path = Path("data/export")` beside `data_dir` (line 19). The API reads
from it; the CLI writes to `--out` (defaulting to this dir in prod). One setting, no other
config surface.

---

### 12. `scripts/export-odbl.sh` (ops) — NEW

**Analog:** `scripts/backup.sh` (host-side bash, `set -euo pipefail`, `docker compose`
wrapper) and `scripts/with-secrets.sh` (Infisical wrapper). D-12's command is
`docker compose run --rm api letmegetin-admin export odbl`, wrapped in
`./scripts/with-secrets.sh` — exactly how `retention.service` invokes it (see §13). The
`backup.sh` `compose()` helper (line 14) is the copy point:

```bash
compose() { docker compose -p "$STACK" -f "$COMPOSE_FILE" "$@"; }
```

No existing script writes into a volume shared with a running container, so the
`--out` directory + volume mapping is the one genuinely new ops detail (Gap 4).

---

### 13. `deploy/systemd/letmegetin-export-odbl.{service,timer}` (ops) — NEW

**Exact analog:** `deploy/systemd/letmegetin-retention.service` — already the "run a CLI
in the api container on the host" pattern:

```ini
[Service]
Type=oneshot
WorkingDirectory=/opt/letmegetin
EnvironmentFile=/etc/letmegetin/infisical.env
ExecStart=/opt/letmegetin/scripts/with-secrets.sh /usr/bin/docker compose -p letmegetin-prod -f docker-compose.prod.yml exec -T api letmegetin-admin retention
```

The export timer copies this, swapping `retention` for `export odbl --out <dir>`. The
`.timer` analog is `letmegetin-retention.timer` (daily `OnCalendar=*-*-* 03:00:00
Persistent=true`); D-12 wants a *weekly snapshot + daily delta* — two calendar lines or two
timer units. This is **fully in-repo** (no need to reach `letmegetin-config`).

---

### 14. `docs/public-api.md` (doc) — MODIFY

Adds the export endpoints to the table (lines 39–50) and an attribution/Produced-Works
section. **Analog:** the existing "Versioning and licence" section (line 173) and the
"Provenance" additive-field section (59–73) — the latter is the template for documenting a
new capability without disturbing the endpoints table. The Produced Works statement
(D-05) belongs here verbatim, matching the wording shipped in `ATTRIBUTION.txt`.

---

### 15. `docs/openapi.json` (generated) — REGENERATE

`scripts/export_openapi.py` (lines 8–15) regenerates it from `app.openapi()`; CI drift is
caught by `tests/integration/api/test_openapi.py` (extend §17).

---

### 16–18. Tests

**Unit (`tests/unit/application/places/test_export.py`):** the CSV writer + manifest +
ZIP assembly are pure — test beside the use case. **Analog:** `test_duplicates.py` layout;
assert CSV quoting (a value containing a comma/quote/newline), manifest row counts, and
that per-answer exclusion omits rows and counts them (D-03).

**Functional (`tests/functional/places/test_export.py`):** the admin CLI + the API route.
**Analog:** `tests/functional/referential/test_admin_cli.py` — `CliRunner().invoke(admin.app, ...)`
+ `tmp_path` (lines 57–72), and the `licence_db` fixture gating on `require_database(...)`
(lines 317–321). A ZIP assertion reads `tmp_path / "..."` with stdlib `zipfile`, asserts the
seven entries, and parses the CSVs back through `csv.DictReader`. The API route test uses
the `client` fixture from `tests/functional/conftest.py` (lines 40–49) with
`require_database("export_event")`.

**Integration (`tests/integration/api/test_openapi.py`):** add
`assert "/api/v1/export/latest.json" in schema["paths"]` and the `{name}.zip` path,
mirroring lines 12–15.

---

## Shared Patterns

### Only canonical places export (D-04)
**Source:** `repositories.py` `list_for_dedup` line 636 and `by_category_country` line 1223 —
`PlaceModel.canonical_id.is_(None)`. **Apply to:** the place/answer/alias extraction SQL.

### Licence filtering is the reviewed matrix, never a code branch (LIC-05 / D-13)
**Source:** `licence.py` `can_redistribute` (18–30) + `licence_repositories.py`
`_may_leave` (23–36) + `redistributable_place_ids` (159–177). **Apply to:** the export's
place filter and per-answer filter. Reuse, do not reimplement.

### Append-only journal, nothing deleted (D-07 / D-08)
**Source:** `PlaceAccessibilityWriteModel` (models 323–347) + `add_contribution` flush
pattern (repositories 1105–1126). **Apply to:** `ExportEventModel` + its writers.

### Read-only CLI commands set `bump=False`
**Source:** `_run_admin` (admin.py 129–157); `coverage`/`licences matrix`/`criterion list`
all pass `bump=False`. **Apply to:** `export odbl` and `place history` (neither mutates the
referential).

### Rate-limited read endpoints reuse `public_rate_limit`
**Source:** `api/deps.py` line 188; `referential.py` lines 30–32. **Apply to:** both export
routes (D-11: "existing anonymous rate limit").

### CSV via stdlib `csv.writer`, streaming, never materialised
**Source:** `coverage.py` 63–72; `import_acceslibre.iter_acceslibre_rows` 173–197. **Apply
to:** every export CSV writer (D-02).

---

## No Analog Found

| File/Concern | Role | Reason |
|--------------|------|--------|
| ZIP assembly (`zipfile`) | batch transform | No `zipfile`/`ZipFile` use anywhere in `src/`; `backup.sh` uses `tar -czf`, not Python. Planner uses stdlib `zipfile` + `io.BytesIO` as the primary, with `iter_acceslibre_rows` streaming as the iterator precedent. |
| `FileResponse` / `StaticFiles` serving | controller | Zero hits for `StaticFiles`/`FileResponse`/`send_file` in `src/`. The export `{name}.zip` route introduces `FileResponse` (or a `StaticFiles` mount) with no in-repo analog. |

---

## Caution / Planner-visible Gaps

1. **Answer-level licence filter has no SQL twin yet.** `_may_leave` (licence_repositories.py
23–36) and `redistributable_place_ids`/`exclusion_counts`/`excluded_ids` (159–198) all
correlate on `PlaceModel.source_license`. D-03 excludes **per answer** — the answer's own
`PlaceAccessibilityModel.source_license` (models.py line 316) must drive a *new*
answer-level predicate (or a `JOIN` over `place_accessibility` + `licence_destination`).
`can_redistribute` (domain) is licence-agnostic and works for both, but the bulk SQL twin
for answers does **not** exist and must be written. The manifest's "excluded-row counts per
source and licence" (D-02) also needs an answer-level `exclusion_counts`, which is not in
the repository today.

2. **No port method returns `criterion_id` for `answers.csv`.** `PlaceAccessibility`
(entities 66–78) carries `criterion_slug` but **not** `criterion_id`; the model
`PlaceAccessibilityModel` has both. D-14 lets `answers.csv` be keyed by slug or numeric id,
but either stable id must come out of a new/extended read method — `list_accessibility`
(910–919) and `list_accessibility_for_places` (921–940) return entities with slug only. The
planner must add a bulk export read that exposes the id (or decide slug-keying and reuse
the existing slug-carrying shape).

3. **Export volume is not wired in `docker-compose.prod.yml`.** The host timer (D-12)
writes into a directory the *API process* also serves via `/api/v1/export/{name}.zip`. No
volume currently mounts an export dir into the `api` service (volumes are only `pgdata`,
see lines 119–120). The planner must add an `export_data` named volume (or bind mount)
shared between the `docker compose run` (timer) and the `api` container, and pass it
through `LETMEGETIN_EXPORT_DIR`.

4. **`export_event` monotone `seq` has no analog.** Every existing journal (`contribution`,
`place_accessibility_write`, `place_merge_log`) uses an autoincrement `id` with no
cross-table monotone guarantee. D-07/D-10 require `seq` to order replay and `--since
<seq>`. The planner must choose a `BigInteger` + `IDENTITY` (or `Sequence`) column; this is
new, not copyable from `place_accessibility_write.id` (which only needs per-row uniqueness).

5. **`--since <seq|date>` ambiguity (D-10).** "seq or date" — the planner must fix whether
`--since` accepts one value type or two flags. The incremental ZIP replays `export_event`
by `seq`; a date must first be mapped to a `seq` boundary. No existing CLI parses
"seq-or-date", so the exact flag spelling is a planner decision (agent's discretion is
silent here).

6. **`latest.json` generator is unassigned.** D-14 leaves "written by the CLI or computed
by the API on read" open. CLI-written (at export time, beside the snapshots) is simpler and
matches D-11 "no per-request generation"; API-computed (scan the export dir on read) avoids
a second write path. Planner must pick one and carry it consistently through §8/§9/§12.

---

## Metadata

**Analog search scope:** `src/letmegetin/domain/**`, `src/letmegetin/application/**`,
`src/letmegetin/infrastructure/persistence/**`, `src/letmegetin/api/**`, `migrations/**`,
`tests/**`, `scripts/**`, `deploy/systemd/**`, `docs/`.
**Files scanned:** admin.py, config.py, main.py, licence.py, licence_repositories.py,
repositories.py (domain + infra), models.py, entities.py (places + referential),
coverage.py, import_acceslibre.py, contribute.py, duplicates.py, referential/admin.py,
referential.py, router.py, deps.py, 0011 migration, test_admin_cli.py, test_openapi.py,
conftest.py, db.py, functional/conftest.py, backup.sh, with-secrets.sh, export_openapi.py,
public-api.md, deploy.md, docker-compose.prod.yml, deploy/systemd/*.
**Pattern extraction date:** 2026-11-14
