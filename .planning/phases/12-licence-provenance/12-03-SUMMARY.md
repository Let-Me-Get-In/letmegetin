---
phase: 12-licence-provenance
plan: 03
subsystem: referential
tags: [licence, odbl, lov2, csv, operator-cli, typer, sqlalchemy, ddd]

# Dependency graph
requires:
  - phase: 12-licence-provenance (plan 01)
    provides: migration 0011's `licence`, `licence_destination` and `source_licence` tables plus the reviewed CSVs
  - phase: 12-licence-provenance (plan 02)
    provides: the write path that resolves a source → licence from `source_licence` at runtime
provides:
  - LicenceRepository port (domain) + SqlAlchemyLicenceRepository (infrastructure)
  - licences.py loaders, sync_licences, audit_licences, format_matrix
  - admin licences sync|matrix|audit operator surface (sync bumps referential_version)
  - seed loads the catalogue, matrix and source mapping before any place import
affects: [12-04 (enforcement predicate reads the matrix), 14 (ODbL export), 15 (lov2 partner feed, AccesLibre feed)]

actuals:
  tokens: 10352   # 41408 chars of realized diff / 4
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Reviewed-CSV → domain objects → repository port: the application layer never imports SQLAlchemy"
    - "Exit-1 audit gate over the licence catalogue and matrix, mirroring `admin families audit`"
    - "Licence catalogue/repository in its own module so the monolithic repositories.py stops growing"

key-files:
  created:
    - src/letmegetin/application/referential/licences.py
    - src/letmegetin/infrastructure/persistence/licence_repositories.py
    - tests/unit/application/referential/test_licences.py
  modified:
    - src/letmegetin/domain/referential/entities.py
    - src/letmegetin/domain/referential/repositories.py
    - src/letmegetin/admin.py
    - src/letmegetin/seed.py
    - tests/unit/application/referential/fakes.py
    - tests/unit/test_seed.py
    - tests/functional/referential/test_admin_cli.py
    - tests/integration/referential/test_seed_vocabulary.py

key-decisions:
  - "Licence/LicenceDestination/SourceLicence dataclasses live in domain/referential/entities.py, not repositories.py, so the port module keeps holding ports only"
  - "audit_licences requires a row for every catalogue licence × destination, not merely one row per licence: a missing pair is an unreviewed pair"
  - "No modification to application/referential/admin.py: the families trio already lives in families.py, so licences.py is imported directly (the plan allowed either)"
  - "sync reads the current tables once to report created/updated/unchanged, rather than having the port return change flags"

requirements-completed: [LIC-05, LIC-03]

coverage:
  - id: D1
    description: "Licence rules are reviewed data loaded through a LicenceRepository port, with a SQLAlchemy adapter that never leaks into the application layer"
    requirement: LIC-05
    verification:
      - kind: unit
        ref: "tests/unit/application/referential/test_licences.py#test_sync_licences_counts_created_then_unchanged"
        status: pass
    human_judgment: false
  - id: D2
    description: "Loaders reject a duplicate slug, an unknown destination, an unknown licence and a bad ISO date"
    requirement: LIC-05
    verification:
      - kind: unit
        ref: "tests/unit/application/referential/test_licences.py#test_load_licence_destinations_rejects_bad_rows"
        status: pass
    human_judgment: false
  - id: D3
    description: "admin licences audit exits 1 on a missing matrix rule or unknown licence reference; audit_licences names each gap"
    requirement: LIC-03
    verification:
      - kind: unit
        ref: "tests/unit/application/referential/test_licences.py#test_audit_licences_reports_a_missing_destination_row"
        status: pass
      - kind: integration
        ref: "tests/functional/referential/test_admin_cli.py#test_licences_audit_names_the_licence_that_lost_a_matrix_row"
        status: pass
    human_judgment: false
  - id: D4
    description: "The LIC-03 row (odbl × lov2_partner = false) is data, provable from the database alone and visible in `admin licences matrix`"
    requirement: LIC-03
    verification:
      - kind: integration
        ref: "tests/functional/referential/test_admin_cli.py#test_licences_matrix_shows_the_lic03_row"
        status: pass
    human_judgment: false
  - id: D5
    description: "The seed populates licence, licence_destination and source_licence from the reviewed CSVs before any place import, and bumps referential_version on a licence-data change"
    requirement: LIC-05
    verification:
      - kind: integration
        ref: "tests/integration/referential/test_seed_vocabulary.py#test_seed_loads_the_reviewed_licence_data"
        status: pass
    human_judgment: false
  - id: D6
    description: "The legal content of the matrix and of the source → licence mapping is right (LIC-03 one-way rule, user → odbl vs lov2_partner)"
    verification: []
    human_judgment: true
    rationale: "The rows are reviewed legal data, not code: an operator and a lawyer must confirm the destination cells before the exported/matched data ships (see 'Licence judgement cells' in the summary)."

duration: 48 min
completed: 2026-11-13
status: complete
---

# Phase 12 Plan 03: Licence catalogue and matrix as reviewed data Summary

**`admin licences sync|matrix|audit` loads the three reviewed CSVs through a `LicenceRepository` port, renders the redistribution matrix incl. the LIC-03 row, and exits 1 on any unreviewed licence or missing matrix rule; the seed loads them before any place import.**

## Performance

- **Duration:** 48 min
- **Started:** 2026-11-13T00:00:00Z (approximate spawn time)
- **Completed:** 2026-11-13
- **Tasks:** 3
- **Files modified:** 11 (3 created, 8 modified)
- **Commits:** 5 measured (`git rev-list --count 7aefcec..HEAD`)

## Accomplishments

- `LicenceRepository` port (`get_by_slug`, `list_licences`, `list_destinations`, `list_source_licences`,
  `allowed`, `upsert_*`) with `Licence` / `LicenceDestination` / `SourceLicence` dataclasses; the
  application layer never imports SQLAlchemy.
- `SqlAlchemyLicenceRepository` in its own module, upserting via `on_conflict_do_update`;
  `allowed()` fails closed for an absent pair (D-15).
- `licences.py`: three CSV loaders validating the closed destination set
  (`open_export`/`osm`/`lov2_partner`) and the catalogue, `sync_licences` with
  created/updated/unchanged counters, `audit_licences` returning one line per gap, and
  `format_matrix` grouped by destination.
- `admin licences sync|matrix|audit`: `sync` runs through `_run_admin` with the default `bump=True`
  (so a licence-data change bumps `referential_version` and invalidates the category grids), `matrix`
  and `audit` run with `bump=False`, `audit` raises `typer.Exit(code=1)` on any gap.
- `seed()` loads the catalogue, the nine matrix rows and the source mapping right after
  `_load_category_mapping`, before `apply_families` and `rebuild_category_grids` — hence before any
  place import can resolve a licence.
- 18 unit tests, 4 functional CLI tests and 1 seed integration test added; full suite 317 passed.

## Task Commits

1. **Task 1: LicenceRepository port + SQLAlchemy impl + loaders/sync/audit/matrix** - `a6408a3` (feat)
2. **Task 2: `admin licences sync|matrix|audit` + seed integration** - `9924110` (feat)
3. **Task 3: Functional CLI coverage for the licence gate** - `454ecf0` (test)

Follow-up commits inside the same plan:

4. `5c4ede9` (test) - seed unit tests stub the new licence sync (fake session has no licence tables)
5. `3f57999` (test) - integration assertion that the seed loads the reviewed licence data

**Plan metadata:** committed separately by the orchestrator.

## Verification

| Command | Result |
|---|---|
| `uv run pytest tests/unit/application/referential/test_licences.py -m unit -q` | 18 passed |
| `uv run pytest tests/functional/referential/test_admin_cli.py -m functional -q` | 11 passed |
| `uv run pytest -q` (whole suite, test DB at 0011) | 317 passed |
| `uv run mypy` | Success: no issues found in 78 source files |
| `uv run ruff check .` / `ruff format --check` on touched files | clean |
| `uv run bandit -r src -c pyproject.toml` | 0 issues |
| `LETMEGETIN_DATABASE_URL=…/letmegetin_test uv run python -m letmegetin.seed` | `seed ok: … mapping=158 licences=0c/0u …` (idempotent after the earlier sync) |
| `python -m letmegetin.admin licences sync / audit / matrix` | `created=10 updated=2 unchanged=2`; `licences ok`; matrix printed |

## Files Created/Modified

- `src/letmegetin/domain/referential/entities.py` - `Licence`, `LicenceDestination`, `SourceLicence`
- `src/letmegetin/domain/referential/repositories.py` - `LicenceRepository` port
- `src/letmegetin/application/referential/licences.py` - loaders, `sync_licences`, `audit_licences`, `format_matrix`
- `src/letmegetin/infrastructure/persistence/licence_repositories.py` - `SqlAlchemyLicenceRepository`
- `src/letmegetin/admin.py` - `licences_app` typer group (sync, matrix, audit)
- `src/letmegetin/seed.py` - `_load_licence_data` called before the family/grid steps
- `tests/unit/application/referential/test_licences.py` - 18 unit tests
- `tests/unit/application/referential/fakes.py` - `FakeLicenceRepository`
- `tests/functional/referential/test_admin_cli.py` - `licence_db` fixture + 4 CLI tests
- `tests/unit/test_seed.py` - licence sync stubbed in the fake-session fixture
- `tests/integration/referential/test_seed_vocabulary.py` - seed → licence tables assertion

## Decisions Made

- **Dataclasses in `entities.py`, port in `repositories.py`.** The plan listed both in
  `repositories.py`; the module is ports-only in this codebase, so the entities follow the existing
  convention instead.
- **`audit_licences` demands a full matrix.** A catalogue licence must have a row for *each* of the
  three destinations, not one row anywhere: a missing pair is a pair nobody reviewed. This is stricter
  than "no matrix row at all" and strictly safer (a missing row already fails closed at read time).
- **`sync` counts by reading first.** One `list_*` per table before the upsert loop keeps the port
  free of change flags while still reporting created/updated/unchanged.
- **No `application/referential/admin.py` change.** The plan allowed importing from `licences.py`
  directly, which is where the families trio equivalent already lives.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] TDD RED commit folded into the GREEN commit (Task 1)**
- **Found during:** Task 1 commit
- **Issue:** The `test(licence)`-then-`feat(licence)` split is impossible here: the pre-commit
  `mypy` hook checks the whole tree and pre-commit stashes unstaged changes, so a test-only commit
  saw the new `licences.py` importing names from the *stashed* `entities.py`.
- **Fix:** RED was still run and observed (`ImportError: cannot import name 'Licence'`), then the
  tests and the implementation were committed together as `a6408a3` (`feat(licence)`).
- **Files modified:** none beyond the task's own files.
- **Verification:** RED observed before the implementation; GREEN after (18 passed).
- **Committed in:** `a6408a3`

**2. [Rule 1 - Bug] Seed unit tests broke on the new licence load (Task 2)**
- **Found during:** whole-suite run after Task 2
- **Issue:** `tests/unit/test_seed.py` drives `seed()` with a fake session and a minimal temp data
  dir: the licence CSVs are absent and the fake session has no `licence` tables, so `_load_licence_data`
  raised `FileNotFoundError` (5 tests).
- **Fix:** the existing autouse `_skip_persistence` fixture now stubs `sync_licences` and the three
  loaders, exactly as it already stubbed `apply_families`/`rebuild_category_grids`. The real seed path
  is covered by `tests/integration/referential/test_seed_vocabulary.py`.
- **Files modified:** `tests/unit/test_seed.py`
- **Verification:** `uv run pytest tests/unit/test_seed.py -m unit -q` → 10 passed; full suite green.
- **Committed in:** `5c4ede9`

**3. [Rule 2 - Missing Critical] `sync` takes three named file options instead of three `--file` flags**
- **Found during:** Task 2
- **Issue:** The plan asked for a `--file` override per CSV; Typer cannot register three `--file`
  options on one command.
- **Fix:** `--licences`, `--destinations`, `--sources`, each defaulting to the reviewed file under
  `settings.data_dir`.
- **Files modified:** `src/letmegetin/admin.py`
- **Verification:** `python -m letmegetin.admin licences --help` / `licences sync --help`.
- **Committed in:** `9924110`

### Scope addition (documented, not auto-fixed)

**4. Seed licence integration test** (`3f57999`) — added a 12-line assertion to the existing seed
integration suite so the "seed populates all three licence tables before an import" truth is proven by
a test rather than by a manual run. No production code changed.

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 bug, 1 missing-critical) + 1 test addition.
**Impact on plan:** No behaviour left out; the CLI flag naming and the test-only plumbing are the only
shape changes.

## Issues Encountered

- `gitnexus` index was 27 commits behind `HEAD`; reindexed (`node .gitnexus/run.cjs analyze --index-only`)
  before running `impact` on `seed` (risk LOW) and `SqlAlchemyFilterRepository` (risk LOW).
- The pre-commit mypy hook checks the whole tree, which forces implementation and tests into one
  commit per task (see deviation 1).

## Licence judgement cells (for human legal review)

No CSV row was added or edited by this plan — the rows below were committed with 12-01 (migration
`0011`) and this plan makes them **enforced by an exit-1 gate**. Flagged because the gate now turns
each cell into a hard rule:

| Cell | Value | Judgement to review |
|---|---|---|
| `odbl × lov2_partner` | **false** | The LIC-03 one-way rule. Because `user → odbl`, this also withholds **user contributions** from a lov2 partner feed — CONTEXT already defers that question to Phase 15 (PART-01). Review before a lov2 feed ships: either give user contributions their own licence slug or add a source dimension to the matrix. |
| `cdla × lov2_partner` | **false** ("Not our data, no partner grant") | Legal judgement: a permissive licence was still refused towards the partner destination. Confirm on what grounds. |
| `cdla × open_export` / `cdla × osm` | **true** | Legal judgement: permissive, no obligation. Confirm attribution is not required for CDLA-Permissive 2.0 in our export format. |
| `odbl × osm` | **true** ("Same licence as OSM") | Legal judgement: ODbL 1.0 content into OSM. Confirm share-alike compatibility both ways. |
| `lov2 × lov2_partner` | **true** ("Our own lov2 data to a lov2 destination") | Legal judgement: our own Etalab data to a partner under the same licence. Confirm attribution-only is enough. |
| *audit completeness rule itself* | catalogue × 3 destinations | Design judgement: the gate refuses to pass a licence that has *no* row for a destination, even though the runtime would fail closed anyway. A stricter review requirement, not a widening. |

## Known Stubs

None.

## Threat Flags

None — no new network endpoint, auth path or trust boundary. The CSV → table boundary is the one the
plan's `T-12-03` threat already covers, mitigated by the closed-set validation in the loaders, the
`destination` CheckConstraint and the exit-1 audit.

## Next Phase Readiness

- `SqlAlchemyLicenceRepository.allowed()` and the `licence_destination` table are ready for 12-04's
  enforcement predicate and its SQL twin.
- Adding or changing a destination/source mapping is now a reviewed CSV change plus
  `admin licences sync`; `admin licences audit` is the gate to run in CI or before an export.
- Open question carried to Phase 15: `user → odbl` versus the `lov2_partner` destination (see the
  judgement table above).

## Self-Check: PASSED

- Files exist: `src/letmegetin/application/referential/licences.py`,
  `src/letmegetin/infrastructure/persistence/licence_repositories.py`,
  `tests/unit/application/referential/test_licences.py` — all found.
- Commits reachable from HEAD: `a6408a3`, `9924110`, `454ecf0`, `5c4ede9`, `3f57999` — all found.
- Plan verification re-run: unit 18 passed, functional 11 passed, `mypy` clean, full suite 317 passed.

---
*Phase: 12-licence-provenance*
*Completed: 2026-11-13*
