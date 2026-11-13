---
phase: 12-licence-provenance
plan: 04
subsystem: places
tags: [licence, redistribution, odbl, lov2, fail-closed, sql-twin, operator-cli, typer, sqlalchemy]

# Dependency graph
requires:
  - phase: 12-licence-provenance (plan 01)
    provides: migration 0011 + the `licence`, `licence_destination`, `source_licence` tables and `place.source_license`
  - phase: 12-licence-provenance (plan 03)
    provides: the reviewed matrix loaded by `admin licences sync` and the LicenceRepository port
provides:
  - domain/places/licence.py — pure, fail-closed `can_redistribute(licence, destination, matrix)` + `DESTINATIONS`
  - SqlAlchemyLicenceRepository.redistributable_place_ids() — the SQL twin as a JOIN for bulk extraction
  - exclusion_counts() / excluded_ids() — the D-14 exclusion manifest (per source/licence, and per id)
  - `admin licences excluded --destination <dest> [--verbose]` operator surface
affects: [14 (open export calls the twin), 15/16/17 (feeds/imports call the predicate)]

actuals:
  tokens: 4673   # 18695 chars of realized diff / 4
  tasks: 2
  commits: 2
plan_head_before: ae0fa48d20097a117cbb29fcd60cf910e57f939f
plan_head_after: 5ee25b2bd9a5f7e1626e946c1a3957b6ffcd96c2

tech-stack:
  added: []
  patterns:
    - "One rule, two speeds (D-13): a pure domain predicate is the reference, the repository holds the identical EXISTS/JOIN twin"
    - "Fail-closed by absence (D-15): no matrix row means no — NULL, unknown licence and unknown destination all match nothing"
    - "Exclusion manifest as a report, never an exception: forbidden rows are counted and listable, they never fail a run (D-14)"

key-files:
  created:
    - src/letmegetin/domain/places/licence.py
    - tests/unit/domain/places/test_licence.py
    - tests/functional/places/test_redistribution.py
  modified:
    - src/letmegetin/infrastructure/persistence/licence_repositories.py
    - src/letmegetin/domain/referential/repositories.py
    - src/letmegetin/admin.py
    - src/letmegetin/application/referential/licences.py

key-decisions:
  - "The SQL twin is one correlated EXISTS on `licence_destination` (`_may_leave`); its negation is the exclusion manifest, so allow and exclude cannot drift apart"
  - "`redistributable_place_ids` returns ids through a JOIN rather than a domain-level predicate over rows: Phase 14 gets the filter, not a re-implementation"
  - "`DESTINATIONS` moved to the domain module and `LICENCE_DESTINATIONS` now aliases it, so the closed destination set has one definition"
  - "`admin licences excluded` refuses an unknown destination with exit 1: a typo would otherwise report every row as excluded"

requirements-completed: [LIC-02, LIC-03]

coverage:
  - id: D1
    description: "A pure `can_redistribute` predicate, fail-closed on NULL/unknown/missing rule, with LIC-03 proven as a reviewed matrix row"
    requirement: LIC-02
    verification:
      - kind: unit
        ref: "tests/unit/domain/places/test_licence.py"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_redistribution.py#test_the_lic03_row_keeps_odbl_rows_out_of_a_lov2_destination"
        status: pass
    human_judgment: false
  - id: D2
    description: "The SQL twin (`JOIN licence_destination`) excludes disallowed and unknown-licence rows for bulk extraction"
    requirement: LIC-02
    verification:
      - kind: integration
        ref: "tests/functional/places/test_redistribution.py#test_the_sql_twin_agrees_with_the_domain_predicate_on_every_matrix_row"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_redistribution.py#test_a_null_or_unknown_licence_matches_no_destination"
        status: pass
    human_judgment: false
  - id: D3
    description: "The exclusion manifest counts excluded rows per source/licence and `admin licences excluded --verbose` lists the excluded ids"
    requirement: LIC-03
    verification:
      - kind: integration
        ref: "tests/functional/places/test_redistribution.py#test_the_manifest_counts_excluded_rows_per_source_and_licence"
        status: pass
      - kind: e2e
        ref: "tests/functional/places/test_redistribution.py#test_the_operator_lists_the_excluded_ids_for_a_destination"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-11-13
status: complete
---

# Phase 12 Plan 04: Licence redistribution enforcement Summary

**One fail-closed `can_redistribute` predicate, its SQL JOIN twin, and an `admin licences excluded` manifest that counts and lists what a destination may not take — with LIC-03 proven as a reviewed `licence_destination` row.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-11-13T12:12:00Z
- **Completed:** 2026-11-13T12:26:38Z
- **Tasks:** 2
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments

- `domain/places/licence.py`: `can_redistribute(licence, destination, matrix)` — stdlib-only, matrix injected, refusing NULL, unknown licence, absent pair and absent matrix (D-15). `DESTINATIONS` names the closed set.
- `SqlAlchemyLicenceRepository._may_leave()` is the same rule as one correlated `EXISTS` (bound parameters only, T-12-04), with `redistributable_place_ids()` as the JOIN form for bulk extraction and `exclusion_counts()` / `excluded_ids()` as its negation (D-13, D-14).
- `admin licences excluded --destination <dest> [--verbose]`: per-source/licence totals, then the excluded ids and their licence; an unknown destination exits 1. Read-only (`bump=False`).
- The functional test seeds one place per matrix licence plus the NULL and unknown-licence cases, and asserts domain predicate, row-level SQL and JOIN agree on **every** reviewed pair; the unit test reads `licence_destinations.csv` so LIC-03 is proven from data, never from a literal.

## Task Commits

1. **Task 1: Pure `can_redistribute` predicate (fail-closed)** - `52655bc` (feat)
2. **Task 2: SQL twin + exclusion manifest + `admin licences excluded`** - `5ee25b2` (feat)

**Plan metadata:** committed separately with this SUMMARY.

## Verification

| Command | Result |
|---|---|
| `uv run pytest tests/unit/domain/places/test_licence.py -m unit -x` | 18 passed |
| `uv run pytest tests/functional/places/test_redistribution.py -m functional -x` | 7 passed |
| `uv run mypy` | Success: no issues found in 79 source files |
| `uv run ruff check … && ruff format --check …` | clean |
| `uv run pytest -m "unit or functional or integration"` | 342 passed |
| `node .gitnexus/run.cjs detect-changes --scope all` | 6 files, 9 symbols, risk medium (only the `licences audit` flows; covered by the functional suite) |

## Files Created/Modified

- `src/letmegetin/domain/places/licence.py` - pure fail-closed predicate + the closed destination set
- `tests/unit/domain/places/test_licence.py` - table-driven over the reviewed CSV, plus the refusal cases
- `src/letmegetin/infrastructure/persistence/licence_repositories.py` - `_may_leave`, `redistributable_place_ids`, `exclusion_counts`, `excluded_ids`
- `src/letmegetin/domain/referential/repositories.py` - the three manifest/twin methods on the `LicenceRepository` port
- `src/letmegetin/admin.py` - `licences excluded` command
- `src/letmegetin/application/referential/licences.py` - `LICENCE_DESTINATIONS` now aliases the domain `DESTINATIONS`
- `tests/functional/places/test_redistribution.py` - predicate ↔ SQL agreement, LIC-03, manifest, CLI

## Decisions Made

- The exclusion manifest is the **negation of the same EXISTS** the twin uses (`~_may_leave`), so "allowed" and "excluded" are exhaustive by construction instead of two queries that can drift.
- `redistributable_place_ids()` returns place ids, not rows: Phase 14/15 can build their own projections on the filter without the rule living anywhere but the matrix.
- `DESTINATIONS` lives in the domain module; the application-layer `LICENCE_DESTINATIONS` aliases it so the closed set is defined once.
- Scope kept to the operator query: the Phase 14 export manifest and import-report counters stay deferred (12-CONTEXT `deferred`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Integrity] `LICENCE_DESTINATIONS` aliased to the new domain `DESTINATIONS`**
- **Found during:** Task 2
- **Issue:** The plan asked for `DESTINATIONS` in `domain/places/licence.py`, which would have left a second copy of the closed destination set in `application/referential/licences.py` — a set the CSV validator and a DB CheckConstraint both enforce.
- **Fix:** `application/referential/licences.py` now imports `DESTINATIONS` from the domain module and keeps `LICENCE_DESTINATIONS` as an alias (1 line + import), so the set has one definition.
- **Files modified:** `src/letmegetin/application/referential/licences.py` (outside the plan's `files_modified`)
- **Verification:** `uv run pytest -m "unit or functional or integration"` — 342 passed, including `admin licences sync|audit|matrix`.
- **Committed in:** `5ee25b2` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 integrity)
**Impact on plan:** No behaviour change; removes a duplicated constant. No scope creep.

## Issues Encountered

None.

## Known Stubs

None — no stub, skipped test or unrun verification in this plan.

## Threat Flags

None — the surface added (`admin licences excluded`) is read-only and was in the plan's threat model (T-12-04 bound parameters, T-12-05 fail-closed).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 14 (open export) and 15-17 (feeds/imports) import `can_redistribute` / call `redistributable_place_ids` and `exclusion_counts`; neither needs to know the rule.
- Open question carried from 12-CONTEXT: user contributions are stamped `odbl`, so the reviewed matrix refuses them at `lov2_partner` — decide the user-contribution licence (or a source dimension in the matrix) before PART-01 ships a lov2 feed.

---
*Phase: 12-licence-provenance*
*Completed: 2026-11-13*

## Self-Check: PASSED
