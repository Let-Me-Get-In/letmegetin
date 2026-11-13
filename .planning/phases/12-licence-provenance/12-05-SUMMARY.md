---
phase: 12-licence-provenance
plan: 05
subsystem: places
tags: [provenance, licensing, conflict-resolution, freshness, write-journal, acceslibre]

# Dependency graph
requires:
  - phase: 12-licence-provenance
    plan: 02
    provides: upsert_accessibility carrying source/actor/observed_at, licence resolved from source_licence
provides:
  - ownership by current source on the one answer write path (a contribution takes ownership, an import may only replace its own rows)
  - same-source freshness on observed_at with NULL as the oldest claim, every NULL combination explicit
  - insert-if-absent across sources, so federated sources still complement each other
  - append-only place_accessibility_write journal on every attempt, accepted or rejected
affects: [13 record UI, 14 ODbL export, 15 acceslibre feed, 16 osm, 17 overture]

actuals:
  tokens: 4685
  tasks: 2
  commits: 2
  plan_head_before: 0c559dd0c1b8901ff64eada21c7789f7fb275a32
  plan_head_after: 3d16fcdc3331204a7c439ced94e3cd738f550c12

tech-stack:
  added: []
  patterns:
    - "One shared write path: ownership, freshness and the journal live in upsert_accessibility, so no importer re-implements them (D-09)"
    - "A pure module helper (_rejection) decides the outcome from the current row's source/observed_at; the repository only reads and writes"
    - "An adjudicated write is split into two bulk statements: the accepted upsert and the journal insert, so a bulk import keeps two round trips per place"

key-files:
  created:
    - tests/functional/places/test_provenance_conflict.py
  modified:
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/domain/places/repositories.py
    - tests/functional/places/test_provenance_conflict.py

key-decisions:
  - "Ownership is decided against the current row's source, never the place's source: a contribution on one criterion takes that row, while an import still inserts the criteria the place lacks (D-09/D-11)."
  - "NULL observed_at is the oldest possible claim, not 'unknown': incoming NULL over a set current value is stale; NULL vs NULL compares equal so replaying a file stays idempotent (D-10)."
  - "Every attempt is journaled, including an accepted replay; the journal is the append-only record of what was proposed, not of what changed (D-12)."
  - "The losing value's resolved licence is journaled with it, so an operator sees what would have been written and under which terms."
  - "reason='not_redistributable' stays reserved in the CheckConstraint with no producer this phase; 12-04 owns the redistribution predicate."

requirements-completed: [LIC-04]

coverage:
  - id: D1
    description: "An import cannot overwrite a row owned by another source (user contribution or another importer) on any criterion the place already holds."
    requirement: LIC-04
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_an_import_cannot_overwrite_a_user_row"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_a_reimport_cannot_revert_a_contribution"
        status: pass
    human_judgment: false
  - id: D2
    description: "Same-source replacement requires an observed_at at least as fresh, with all four NULL combinations defined; an older file is rejected as stale, never silently rolled back."
    requirement: LIC-04
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_same_source_freshness_treats_null_as_the_oldest"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_an_older_file_is_rejected_as_stale"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_an_incoming_null_observed_at_is_rejected_as_stale"
        status: pass
    human_judgment: false
  - id: D3
    description: "An import inserts a criterion the place does not hold yet, so sources complement each other while existing values stay protected."
    requirement: LIC-04
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_an_import_inserts_a_missing_criterion_without_overwriting_the_owned_one"
        status: pass
    human_judgment: false
  - id: D4
    description: "A user contribution takes ownership of an Acceslibre answer (source='user', actor='user:<id>') and is accepted, not rejected as other_source."
    requirement: LIC-04
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_a_contribution_takes_ownership_of_an_imported_answer"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_a_contribution_takes_ownership_from_another_source"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every attempted write appends a place_accessibility_write row with its decision and reason, and the losing value stays visible."
    requirement: LIC-04
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_replaying_the_same_file_keeps_the_value_and_journals_each_attempt"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_provenance_conflict.py#test_a_reimport_cannot_revert_a_contribution"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-11-13
status: complete
---

# Phase 12 Plan 05: Conflict and freshness on the shared write path Summary

**A re-import can no longer clobber a human contribution or roll a row back: ownership, freshness and insert-if-absent are enforced once in `upsert_accessibility`, and every losing value is journaled.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-11-13T12:16Z
- **Completed:** 2026-11-13T12:31Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 1 extended, 2 touched)

## Accomplishments

- `upsert_accessibility` now reads the current row's `source`/`observed_at` per criterion and adjudicates every value before writing: a contribution takes ownership, an import may only replace a row of its own source, and a same-source replacement needs an `observed_at` at least as fresh (NULL as the oldest claim).
- A criterion the place does not hold is always inserted, so a user contribution on one criterion never blocks an import from filling the others (D-11).
- Every attempt — accepted or rejected — appends a `place_accessibility_write` row carrying the incoming value, source, resolved licence, actor and `decision`/`reason`, so `stale` and `other_source` losses stay visible to an operator (D-12).
- `tests/functional/places/test_provenance_conflict.py` proves the whole matrix twice: directly on the shared path, then end-to-end through the Acceslibre importer and `contribute`, including all four `observed_at` NULL combinations and the idempotent replay.

## Task Commits

Each task was committed atomically:

1. **Task 1: Ownership + freshness (all NULL combos) + insert-if-absent** — `fc86327` (feat)
2. **Task 2: Conflict matrix functional test + write-journal assertion** — `3d16fcd` (test)

**Plan metadata:** committed by the orchestrator with STATE/ROADMAP.

_Note: both tasks were TDD (`tdd="true"`): the rule tests were written and run RED before the implementation, then extended RED→GREEN for the end-to-end matrix._

## Files Created/Modified

- `src/letmegetin/infrastructure/persistence/repositories.py` — `upsert_accessibility` rewritten into an adjudicated per-criterion write plus two bulk statements (accepted upsert, journal insert); `_rejection` holds the ownership/freshness rule; `_USER_SOURCE` names the ownership-taking source.
- `src/letmegetin/domain/places/repositories.py` — the `PlaceRepository` port docstring states the four rules so both callers know what the one write path guarantees.
- `tests/functional/places/test_provenance_conflict.py` — 14 functional tests: 9 on the shared path (ownership, six freshness cases, insert-if-absent, two contribution-ownership cases) and 5 end-to-end through the importer/`contribute`.

## Decisions Made

- **Ownership is per row, not per place.** Adjudicating against the current row's `source` is what makes D-09 and D-11 coexist: the protected thing is an existing answer, not the whole place.
- **NULL is the oldest claim, not "unknown".** This gives the four defined combinations with no extra flag, and keeps a same-file replay idempotent.
- **Journal every attempt, including accepted replays.** The journal records what was proposed, which is what an operator needs to answer "why is this value not the source's?".
- **Two bulk statements per call** (accepted upsert + journal insert) instead of one row-at-a-time loop, so the national import does not gain a per-criterion round trip.

## Deviations from Plan

### 1. [Plan-internal contradiction → resolved in favour of D-12] An idempotent replay is journaled

- **Found during:** Task 2.
- **Issue:** Task 2's behaviour text says a same-file replay adds "no new journal row beyond the first accepted write", while D-12 and this plan's `must_haves` say every attempted write appends a `place_accessibility_write` row.
- **Fix:** Journal every attempt; the replay test asserts the value and `observed_at` are unchanged and that the journal holds two `accepted` rows with no rejection. The stored answer is what idempotence is measured on.
- **Files modified:** `tests/functional/places/test_provenance_conflict.py`.
- **Verification:** `test_replaying_the_same_file_keeps_the_value_and_journals_each_attempt`.
- **Committed in:** `3d16fcd`.

### 2. [No-op scope] `contribute.py` and `import_acceslibre.py` needed no change

- **Found during:** Task 2.
- **Issue:** The plan listed both files as task files, with "finish the provenance plumbing if needed".
- **Fix:** 12-02 already passes `source`, `actor` and `observed_at` through both callers, and the rewritten signature is unchanged. No source edit was made, so the task commit touches only the test file.
- **Verification:** `uv run pytest -q` — 356 passed, including the existing import and provenance-write suites.

**Total deviations:** 1 interpretation conflict (resolved per D-12), 1 no-op scope note. No auto-fixed bugs, no architectural change, no new dependency.

## Issues Encountered

None. The existing `test_places_import.py` re-import case (two imports with a NULL `date_maj`) still passes because NULL vs NULL compares equal.

## User Setup Required

None.

## Next Phase Readiness

- Phases 15–17 can re-import federated sources through the same call: ownership and freshness are data rules in one place, not a promise each importer keeps.
- `reason='not_redistributable'` remains reserved with no producer; the redistribution predicate from 12-04 is the one that will produce it if a write path is ever gated on it.
- Deferred open question (recorded in 12-CONTEXT): a user row is stamped `odbl`, and the reviewed matrix refuses `odbl × lov2_partner`; before PART-01 ships a lov2 feed, decide whether contributions need their own licence slug or a source dimension in the matrix.

---
*Phase: 12-licence-provenance*
*Completed: 2026-11-13*

## Self-Check: PASSED

- SUMMARY.md and the functional test file exist on disk.
- Commits `fc86327` and `3d16fcd` are ancestors of HEAD.
- `uv run pytest -q` — 356 passed; `uv run mypy` — 79 files clean; `uv run ruff check` — clean.
