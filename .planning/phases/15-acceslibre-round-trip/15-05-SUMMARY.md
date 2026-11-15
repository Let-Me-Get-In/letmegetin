---
phase: 15-acceslibre-round-trip
plan: 05
subsystem: api
tags: [acceslibre, push, read-then-diff, journal, licence-gate, streaming, typer, alembic]

# Dependency graph
requires:
  - phase: 15-acceslibre-round-trip
    provides: AccesLibrePort, AccesLibrePushRepositoryPort, resolve_identifier, diff_fields, freshness_decision, validate_value, push_payload (15-02); place.erp_slug and the recorded identifier rule (15-03, 15-04)
provides:
  - the `acceslibre_push_write` append-only journal (model + migration 0015), with its own CHECKs
  - `SqlAlchemyPushRepository.stream_owned_answers(destination)` and `append(...)`
  - `push_acceslibre()` — read, typed diff, freshness, PATCH what differs, journal every decision
  - `acceslibre push [--dry-run]`, the operator command
affects: [15-06-dual-licence-restamp, 16-osm-export]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2
  plan_head_before: 9f046e2dfada1722d559c9c9b094e01e5e897031
  plan_head_after: 5b24f89e970f786b65008669e656102f741e7bd6

tech-stack:
  added: []
  patterns:
    - "the licence gate lives in the stream predicate, so a withheld answer never reaches the use case"
    - "the use case takes both domain ports, so the functional test substitutes a fake and still exercises the real DB"
    - "one GET and one PATCH per place: the stream is ordered by canonical id and grouped, not one call per answer"

key-files:
  created:
    - migrations/versions/0015_acceslibre_push_write.py
    - src/letmegetin/infrastructure/persistence/push_repositories.py
    - src/letmegetin/application/places/push_acceslibre.py
    - tests/functional/places/test_acceslibre_push.py
  modified:
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/domain/places/acceslibre_push.py
    - src/letmegetin/admin.py

key-decisions:
  - "The journal is a new table, never a widening of `place_accessibility_write`: its CHECKs cannot express `skipped` or `their_fresher` (Pitfall 6)."
  - "The stream filters `source='user'` AND `_licence_allows(source_license, destination)`, so a withheld licence is never pushed and never journaled — the `not_redistributable` reason stays in the vocabulary for a future refusal path."
  - "Validate before diffing: `diff_fields` normalises and would raise on an out-of-type value, so `validate_value` runs first and a rejection becomes a `skipped`/`invalid_value` row instead of aborting the run."
  - "A 403 from PATCH is journaled `rpa_locked` and the run continues; any other DomainError propagates, because a retry or a different identifier cannot fix it."
  - "Their `updated_at` is parsed to naive UTC before `freshness_decision`, otherwise a `+01:00` offset would raise a naive/aware TypeError against our `recorded_at`."
  - "Idempotency is the diff: the fake API applies a PATCH, so the replay sees `\"true\"` normalised to `True` and patches nothing."

requirements-completed: [PART-02]

coverage:
  - id: D1
    description: "`acceslibre_push_write` is a new append-only table with `decision IN ('accepted','skipped')` and the five-reason CHECK; migration 0015 applies from 0014 and downgrades"
    requirement: PART-02
    verification:
      - kind: other
        ref: "uv run alembic upgrade head; uv run alembic downgrade 0014; uv run alembic upgrade head; psql \\d acceslibre_push_write on letmegetin_test"
        status: pass
    human_judgment: false
  - id: D2
    description: "`stream_owned_answers(destination)` streams the winning `source='user'` answer per canonical place and criterion, licence-gated by the destination parameter, merged places remapped, `yield_per(1000)`; `append` writes one journal row"
    requirement: PART-02
    verification:
      - kind: functional
        ref: "tests/functional/places/test_acceslibre_push.py#test_a_merged_place_pushes_under_its_canonical_identifier"
        status: pass
      - kind: functional
        ref: "tests/functional/places/test_acceslibre_push.py#test_a_withheld_licence_is_never_pushed"
        status: pass
    human_judgment: false
  - id: D3
    description: "`acceslibre push [--dry-run]` GETs at `resolve_identifier`, diffs typed values, applies amended-D-11 freshness, PATCHes only differing fields, journals every decision with the value we held, and writes nothing on a dry run"
    requirement: PART-02
    verification:
      - kind: functional
        ref: "tests/functional/places/test_acceslibre_push.py (9 tests: dry-run, replay idempotency, journal value, withheld licence, blocked rule, invalid value, RPA 403, missing key, merged place)"
        status: pass
      - kind: unit
        ref: "tests/unit/domain/places/test_acceslibre_push.py (36 tests, unchanged decision module)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A no-op PATCH on staging confirms A1 (200 + ErpImport body) and the `accessibilite` key name before the first production push"
    verification: []
    human_judgment: true
    rationale: "Plan Task 3 is a `checkpoint:human-action gate=blocking-human`. No AccesLibre API key exists (LET-130), so the no-op PATCH was NOT run and NOT simulated; A1 and Pitfall 8's key name remain unconfirmed."

duration: 27min
completed: 2026-11-15
status: halted
---

# Phase 15 Plan 05: AccesLibre outbound push Summary

**The operator push now exists: it reads each ERP at the probe's identifier, diffs typed values, lets amended-D-11 freshness settle conflicts, patches only what differs, and journals every decision into a new append-only table — with the live write contract (A1) still gated on a human no-op PATCH.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-11-15T19:48:06Z
- **Completed:** 2026-11-15T20:15:00Z
- **Tasks:** 2 of 3 (Task 3 is the blocking-human PATCH contract check, not executed)
- **Files modified:** 7 (4 created)

## Accomplishments

- **Migration `0015`** creates `acceslibre_push_write`: `decision IN ('accepted','skipped')` and `reason IS NULL OR reason IN ('their_fresher','rpa_locked','not_redistributable','unmappable','invalid_value')`, plus `place_id` / `criterion_id` FKs and the `value` JSONB that keeps the losing side. Applied from `0014`, downgraded, re-applied; the shape was checked column by column on `letmegetin_test`. `place_accessibility_write` was not touched.
- **`SqlAlchemyPushRepository`** implements the 15-02 port. `stream_owned_answers(destination)` ranks one winner per `(canonical place, criterion)` over `source='user'` rows, gates on `_licence_allows(source_license, destination)` with the destination as a bound parameter, remaps merged places onto the canonical id (and its `erp_slug` / `source_id`), and streams with `yield_per(1000)`. `append()` writes one row, resolving the criterion FK once per run.
- **`push_acceslibre()`** groups the streamed answers by place, resolves the target with `resolve_identifier(rule, erp_slug, origin_id)`, GETs once, flattens the `accessibilite` section to the 8 `PUSH_FIELDS`, validates each outbound value, diffs typed values, applies `freshness_decision(observed_at, recorded_at, their_updated_at)`, and PATCHes only the surviving fields. Every branch journals: `accepted`, `their_fresher`, `rpa_locked` (403), `unmappable` (blocked rule, or a criterion outside `FIELD_MAP`), `invalid_value`.
- **`acceslibre push [--dry-run]`** is the only write path. A missing `LETMEGETIN_ACCESLIBRE_API_KEY` raises `DomainError` before the client is constructed (`exit 1`, message names the env var and `15-PARTNER-ASK.md`). `_run_admin(..., bump=False, commit=not dry_run)` gives the dry run its rollback.
- **9 functional tests** against the real PostGIS database with an in-process `AccesLibrePort` fake: dry run prints the diff and writes nothing, a replay patches nothing and adds no accepted event, every decision keeps our value, a withheld licence never leaves, a blocked rule journals `unmappable`, an out-of-type value is refused (not coerced), a locked ERP journals `rpa_locked` and the run continues, a missing key exits 1, and a merged place pushes under its canonical identifier.

## Task Commits

Each task was committed atomically:

1. **Task 1: The outbound journal table, the owned-answer stream, and the journal repository** — `efda87e` (feat)
2. **Task 2: The read-then-diff use case and `acceslibre push [--dry-run]`** — `5b24f89` (feat)
3. **Task 3: Verify the PATCH contract (A1) with a no-op PATCH** — NOT EXECUTED (`checkpoint:human-action gate="blocking-human"`)

**Plan metadata:** the close-out commit carrying this SUMMARY.

## Verification (real output)

| Check | Command | Result |
|---|---|---|
| Migration | `uv run alembic upgrade head` | `Running upgrade 0014 -> 0015` |
| Migration round trip | `uv run alembic downgrade 0014 && uv run alembic upgrade head` | both ran; table recreated |
| Test DB schema | `uv run alembic upgrade head` with `LETMEGETIN_DATABASE_URL=…/letmegetin_test` | `Running upgrade 0014 -> 0015` |
| Lint | `uv run ruff check` (6 touched files) | All checks passed |
| Format | `uv run ruff format --check src tests migrations` | 181 files already formatted |
| Types | `uv run mypy` | Success: no issues found in 94 source files |
| Security | `uv run bandit -r src -c pyproject.toml` | High 0, Medium 0, Low 0 |
| Push functional | `uv run pytest tests/functional/places/test_acceslibre_push.py -m functional -x` | 9 passed |
| Push unit | `uv run pytest tests/unit/domain/places/test_acceslibre_push.py -m unit -x` | 36 passed |
| Full suite | `uv run pytest -q` | 588 passed in 152.25s |
| CLI help | `uv run python -m letmegetin.admin acceslibre --help` | `probe`, `push` listed |
| Missing key | `uv run python -m letmegetin.admin acceslibre push --dry-run` (no key set) | `no AccesLibre API key: …` `exit=1` |

## Files Created/Modified

- `migrations/versions/0015_acceslibre_push_write.py` — revision `0015` from `0014`; creates the table, its two CHECKs and the `place_id` index; drops them on downgrade.
- `src/letmegetin/infrastructure/persistence/models.py` — `AccesLibrePushWriteModel`.
- `src/letmegetin/infrastructure/persistence/push_repositories.py` — `SqlAlchemyPushRepository`, `_owned_answers(destination)`.
- `src/letmegetin/application/places/push_acceslibre.py` — `push_acceslibre()`, `PushReport`, per-place grouping and journaling.
- `src/letmegetin/domain/places/acceslibre_push.py` — `OwnedAnswer.source_license`, `AcceslibrePushWrite.source`/`source_license` (defaulted).
- `src/letmegetin/admin.py` — `acceslibre push`, `_push_summary`.
- `tests/functional/places/test_acceslibre_push.py` — 9 tests, one shared `FakeAccesLibre`.

## Decisions Made

- **The gate is the stream, not a branch in the use case.** A withheld licence produces no row at all, so it cannot be pushed and cannot be journaled; the `not_redistributable` reason stays declared for a future explicit refusal path. This is fail-closed and makes the negative test trivial to trust.
- **Validate, then diff.** `diff_fields` normalises both sides and raises on an out-of-type value, so `validate_value` runs first per field; a bad value becomes one `skipped`/`invalid_value` row and the rest of the place still pushes.
- **A 403 is an RPA lock.** The adapter redacts errors to `HTTP <status>` (never the key or the body), so the use case keys on the status: 403 → journal `rpa_locked` and continue; every other `DomainError` propagates.
- **A GET failure propagates.** A 404 or a 5xx on read aborts the run with the adapter's message rather than inventing a skip reason; the operator sees it and the journal stays truthful.
- **`pushed` counts accepted answers (journal rows), not places**, which is what the journal records and what an operator reconciles against.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The domain dataclasses gained the journal's provenance fields**
- **Found during:** Task 1
- **Issue:** the plan's column list includes `source` and `source_license`, but 15-02's `AcceslibrePushWrite` carried neither, so `append()` had no way to fill them and the columns would always be NULL or defaulted blindly.
- **Fix:** `AcceslibrePushWrite.source` (default `"user"`) and `.source_license` (default `None`); `OwnedAnswer.source_license` (default `None`) so the stream can supply it. Both new fields are defaulted, so no existing construction breaks.
- **Files modified:** `src/letmegetin/domain/places/acceslibre_push.py`
- **Commit:** `efda87e`

**2. [Rule 1 - Bug] Their `updated_at` would have raised a naive/aware comparison**
- **Found during:** Task 2 (writing `freshness_decision`'s caller)
- **Issue:** AccesLibre returns an ISO timestamp with an offset (`…+00:00`); our `recorded_at` is a naive `timestamp without time zone`, so `claim >= theirs_updated_at` raises `TypeError`, aborting every freshness comparison.
- **Fix:** `_parse_timestamp` converts the offset to naive UTC, and returns `None` on an unparseable value (which `freshness_decision` reads as "undated").
- **Verified by:** `test_the_journal_keeps_our_value_on_every_decision` passes an offset-bearing ISO string and asserts `their_fresher`.
- **Commit:** `5b24f89`

### Deviations (recorded, not defects)

**3. [Deviation - Condition] The withheld-licence case is never journaled**
- **Found during:** Task 2
- **Issue:** the plan's Task 2 wording names `not_redistributable` as the reason for a withheld row, but Task 1's acceptance puts the licence gate inside `stream_owned_answers`, so a withheld answer never reaches the use case.
- **Resolution:** the gate stays in the stream (one place, fail-closed, cheaper than streaming 1.7M rows to reject them); the test asserts no PATCH, no GET and no journal row. The reason value remains in the CHECK for a future explicit refusal path.

**4. [Deviation - Shape] One GET and one PATCH per place, not per answer**
- **Found during:** Task 2
- **Issue:** streaming per answer would cost one GET/PATCH per field (up to 8) for the same ERP, and eight single-field PATCHes can interleave with an upstream edit.
- **Resolution:** the stream is ordered by canonical id and grouped; a place's answers become one `ours` mapping, one diff and one PATCH. The dry-run diff is therefore printed per ERP, as D-14 asks.

## Issues Encountered

- **The plan is halted at its designed blocking gate (Task 3).** No AccesLibre API key exists (LET-130), so the no-op PATCH that would confirm A1 and the `accessibilite` key name was NOT run and NOT simulated. `acceslibre push --dry-run` against staging also requires the key, so it was not attempted either. The write contract is therefore still `[ASSUMED]`.
- **GitNexus was reindexed before editing** (`node .gitnexus/run.cjs analyze --index-only`, 5.9 s, 4303 nodes) because the index sat at `64d2b27` against HEAD `9f046e2`. `impact PlaceAccessibilityWriteModel` reported `MEDIUM` with 5 direct importers; this plan only adds a new model class and a new module, so no existing call site changed.
- **Two test fixtures write shared referential state** (`source_licence.user`) and restore the previous row in teardown; the push tests never rely on the committed `user → odbl` value, so they survive 15-06's `dual` change.

## User Setup Required

The key is still the only external input: `LETMEGETIN_ACCESLIBRE_API_KEY` (see `15-PARTNER-ASK.md`), stored in the Infisical project `39c0bbf4-…`, `prod`, path `/`, injected via `scripts/with-secrets.sh`. No key was read, printed or committed by this plan; no test reads one.

## Next Phase Readiness

- **Ready:** `acceslibre push [--dry-run]` is wired end to end and idempotent on a replayed run. 15-06 only touches licence CSVs and a re-stamp migration; the push reads the matrix through `_licence_allows`, so adding `dual × lov2_partner = true` widens it by data alone.
- **Blocked:** the first production PATCH. Resume at Task 3: provide the key, run `acceslibre push --dry-run` on one known place, then a single no-op PATCH of that ERP's current value, report the response body (200 + `ErpImport`, or the actual key name / 4xx), and let the human approve the write contract.
- **Known limit:** the ERP-level `updated_at` is coarse — it moves on any ERP edit, not only an accessibility one, so a `their_fresher` skip may be a field they never touched. That is amended D-11 as decided, not a defect.

---

## Self-Check: PASSED

- `migrations/versions/0015_acceslibre_push_write.py` — FOUND; upgrade/downgrade/upgrade all ran, table verified on `letmegetin_test`.
- `src/letmegetin/infrastructure/persistence/push_repositories.py` — FOUND.
- `src/letmegetin/application/places/push_acceslibre.py` — FOUND.
- `tests/functional/places/test_acceslibre_push.py` — FOUND, 9 passed.
- Commits `efda87e` and `5b24f89` — both ancestors of HEAD; 588 tests, ruff, ruff format, mypy and bandit clean.
- Task 3 — intentionally NOT executed (blocking-human checkpoint).

*Phase: 15-acceslibre-round-trip*
*Completed (partial): 2026-11-15*
