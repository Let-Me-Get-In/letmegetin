---
phase: 14-open-odbl-export
plan: 01
subsystem: database
tags: [postgres, alembic, sqlalchemy, journal, mvcc, odbl, xid8]

# Dependency graph
requires:
  - phase: 12-licence-provenance
    provides: source_license columns and the reviewed source_licence table every write resolves
  - phase: 11-place-detail
    provides: PlaceAccessibilityModel, the single upsert_accessibility answer write path
provides:
  - export_event table (BigInteger IDENTITY seq, xid8 boundary, entity/op CHECK constraints)
  - ExportEvent entity, ExportEventRepository port, describe_changes and _jsonable
  - SqlAlchemyExportEventRepository (append, list_events, list_events_by_slug, safe_seq)
  - full-row journal events appended at every place-write choke point, same transaction
  - letmegetin-admin place history <slug>
affects: [14-02 delta/serving, 14-03 retention, later place-history UI]

actuals:
  tokens: 13000
  tasks: 3
  commits: 4
  plan_head_before: ca6152cb0534870fb43bc05836e7181f02ce5248
  plan_head_after: 46723b56d625e8668f3c68c4475dcec00591c478

tech-stack:
  added: []
  patterns:
    - "MVCC boundary instead of a count: safe_seq() = max(seq) WHERE xid < pg_snapshot_xmin(pg_current_snapshot()) (D-10)"
    - "UserDefinedType returning XID8, defined once in the model and once in the frozen migration (no app import)"
    - "Full-row payloads built from the RETURNING batch of a bulk UPDATE (one query, no per-row re-read)"
    - "Fail-closed append: a payload that cannot serialise aborts the write rather than leaving a journal gap"

key-files:
  created:
    - migrations/versions/0012_export_event.py
    - src/letmegetin/domain/places/export.py
    - src/letmegetin/infrastructure/persistence/export_repositories.py
    - src/letmegetin/application/places/history.py
    - tests/unit/infrastructure/persistence/test_export_event_chokepoints.py
    - tests/unit/application/places/test_history.py
    - tests/functional/places/test_export_event.py
  modified:
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/admin.py

key-decisions:
  - "safe_seq() is a SELECT, so calling it first inside 14-02's REPEATABLE READ transaction pins the snapshot the streamed rows are read from."
  - "set_review_state journals op=merge only when canonical_id is now set, op=update for a reject that actually cleared the candidate, and nothing when all three journaled columns are unchanged."
  - "upsert_accessibility compares value/source/source_license/observed_at against the pre-write row and appends nothing when all four are identical (a no-op contribution is not a change)."
  - "The journal excludes location, name_normalized, created and updated: the payload is referential state, not derived or bookkeeping columns."
  - "The per-place history line diffs every event against the previous one in seq order, as the plan specifies; answer events therefore render as their own row rather than being folded into the place row."

patterns-established:
  - "A new write path that touches PlaceModel fails tests/unit/infrastructure/persistence/test_export_event_chokepoints.py unless it calls _append_export_event(s): the scan is structural (AST), not a review promise (T-14-01)."
  - "Bulk writes use UPDATE … RETURNING and build all journal payloads from one result set (W-N+1)."

requirements-completed: [EXP-01]

coverage:
  - id: D1
    description: "export_event exists with a monotone identity seq, an xid8 server-default boundary and entity/op CHECK constraints"
    requirement: EXP-01
    verification:
      - kind: integration
        ref: "LETMEGETIN_DATABASE_URL=.../letmegetin_test uv run alembic upgrade head && uv run alembic current → 0012 (head); downgrade 0011 → upgrade head round-trips"
        status: pass
    human_judgment: false
  - id: D2
    description: "every place-write choke point appends a same-transaction full-row event; rejected and no-op writes append nothing"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_export_event.py (13 journal cases + the history CLI case)"
        status: pass
      - kind: unit
        ref: "tests/unit/infrastructure/persistence/test_export_event_chokepoints.py"
        status: pass
      - kind: other
        ref: "uv run pytest -q → 430 passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "safe_seq() excludes an in-flight transaction's event and includes it once committed"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "test_safe_seq_publishes_an_event_only_after_its_transaction_commits"
        status: pass
    human_judgment: false
  - id: D4
    description: "letmegetin-admin place history <slug> prints date, op, actor and the changed fields in seq order"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "test_place_history_prints_both_events_in_seq_order"
        status: pass
      - kind: unit
        ref: "tests/unit/application/places/test_history.py (describe_changes, _jsonable, format/place_history)"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-11-14
status: complete
---

# Phase 14 Plan 01: Export journal and per-place history Summary

**Migration 0012 adds the append-only `export_event` journal with an `xid8` MVCC boundary, every place write now appends its full-row event in the write's own transaction, and `letmegetin-admin place history <slug>` reads the journal back as changed-field lines.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3 executed (Task 3 in RED → GREEN commits)
- **Files modified/created:** 10

## Accomplishments

- `export_event`: `seq BIGINT GENERATED … AS IDENTITY` (the replay order), `xid xid8 NOT NULL DEFAULT pg_current_xact_id()`, `occurred_at` from `clock_timestamp()`, CHECK constraints on `entity` and `op`, and `ix_export_event_entity_id_seq`. No foreign key: the journal survives merges and is append-only.
- `safe_seq()` = `max(seq) WHERE xid < pg_snapshot_xmin(pg_current_snapshot())`, on the `ExportEventRepository` port and the SQLAlchemy implementation. Proven against a live in-flight transaction: the event is invisible until its transaction commits.
- Every choke point journals its post-write row: `add` (insert), `update` (update), `set_review_state` (merge, or update for a real reject, nothing for a no-change call), `reassign_category` / `set_duplicate_candidate` / `clear_duplicate_candidates` (one update per affected row, from one `UPDATE … RETURNING`), and `upsert_accessibility` (insert/update per accepted answer, nothing for a rejection or an identical re-submit).
- `_jsonable` is fail-closed: a NaN/Infinity float raises `DomainError` before JSONB ever sees it, so a write cannot commit with a missing journal event.
- `letmegetin-admin place history <slug>` folds the events into `date op actor changed=field` lines, with the diff computed at read time; it runs with `bump=False` and never touches the referential version.
- The chokepoint test is a structural AST scan of `infrastructure/persistence`: it proves `add`/`update` are detected, and its two negative cases show a new `touch()` method (a `update(PlaceModel)` write, or a `model.category_id = …` mutation) fails the scan unless it journals.

## Task Commits

Each task was committed atomically:

1. **Task 1: Journal, model, entity/port, safe_seq, choke-point appends** — `565039b` (feat)
2. **Task 2: Functional proof of in-transaction append, rejects/no-ops, MVCC boundary** — `6cd4e06` (test)
3. **Task 3 (RED): History unit cases + the failing CLI case** — `00f449f` (test)
4. **Task 3 (GREEN): `place history` use case and CLI command** — `46723b5` (feat)

**Plan metadata:** committed separately after this file.

## Verification (real output)

- `uv run alembic upgrade head` → `Running upgrade 0011 -> 0012`; `uv run alembic current` → `0012 (head)` (downgrade to 0011 then upgrade head also round-trips).
- `uv run pytest tests/unit/application/places/test_history.py tests/unit/infrastructure/persistence/test_export_event_chokepoints.py -m unit -q` → **14 passed**.
- `uv run pytest tests/functional/places/test_export_event.py -m functional -q` → **14 passed** (1 third-party deprecation warning).
- `uv run pytest -q` → **430 passed, 1 warning** in 102 s.
- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `157 files already formatted`.
- `uv run mypy` → `Success: no issues found in 83 source files`.
- `uv run bandit -r src -c pyproject.toml` → `Low: 0, Medium: 0, High: 0`.
- `node .gitnexus/run.cjs analyze --index-only` (the index was stale at `764a683`) → `3 557 nodes | 7 341 edges`; `detect-changes --scope all` → `Diff touched 2 file(s) but no indexed symbols overlap those hunks — not a clean tree` (the two files are the orchestrator-owned `.planning/STATE.md` and `.planning/state.json`, not code).

`uv run alembic check` reports only the pre-existing PostGIS `spatial_ref_sys` drift (same as before this plan); it also logs "Couldn't determine database type for column 'export_event.xid'", which is autogenerate declining to compare the custom `XID8` type, not a detected change.

## Decisions Made

- **`_jsonable` accepts a row mapping** and converts per value; the place payload builder feeds it the referential column set, so the same helper serialises ORM models and RETURNING rows.
- **Bulk helpers read `UPDATE … RETURNING`** and return `len(rows)` instead of `rowcount`: one query gives both the count and the exact post-write state the journal must store.
- **`current` in `upsert_accessibility` now also selects `value` and `source_license`**: the no-op comparison needs the full identity tuple, not just source/observed_at.
- **The history command reuses `_run_admin(..., bump=False)`**: read-only, one session, domain errors mapped to exit 1 like every other admin command.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Bulk UPDATE + RETURNING needed a shared payload builder typed for RowMapping**
- **Found during:** Task 1 (mypy gate)
- **Issue:** SQLAlchemy's `RowMapping` is not accepted where `Mapping[str, object]` is expected, and `int(row["id"])` on `object` failed mypy's overload check.
- **Fix:** the private payload helpers take `Any` for the row (`_place_payload`, `_place_update_events`, `_answer_unchanged`), documented as accepting either an ORM model or a RETURNING mapping.
- **Files modified:** `src/letmegetin/infrastructure/persistence/repositories.py`
- **Verification:** `uv run mypy` → no issues in 83 source files.
- **Committed in:** `565039b`

**2. [Rule 3 - Blocking] The first Task 3 RED commit was rejected by pre-commit**
- **Found during:** Task 3 commit
- **Issue:** the ruff hook rewrote the test imports, so pre-commit aborted the commit (by design).
- **Fix:** re-staged the hook-formatted file and re-committed; no `--no-verify`.
- **Files modified:** `tests/unit/application/places/test_history.py` (import order only)
- **Verification:** commit `00f449f` landed with all hooks passing.
- **Committed in:** `00f449f`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** No behavioural change; typing and hook mechanics only. No scope creep.

## Issues Encountered

- None open. The plan's Task 1 verify command's `uv run alembic upgrade head` was run against the test database (`LETMEGETIN_DATABASE_URL=.../letmegetin_test`), per the execution brief.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **14-02** must call `safe_seq()` **first** inside its `REPEATABLE READ` transaction: the SELECT pins the snapshot the streamed rows are read from. `safe_seq()` returns `0` on an empty journal.
- `export_event` has **no foreign key to `place`** (deliberate). Retention (D-15) deletes events by `seq` independently of place rows; any test or cleanup that deletes places must delete their events explicitly, or the journal keeps the rows by design.
- Reading by `entity_id` returns **both** place and answer events; `place history` currently prints them as separate lines rather than folding an answer into the place row. If 14-03 or the later history UI wants per-entity diffs, group by `entity` at read time.
- All place-write paths now journal, including test fixtures' imports: a test asserting a globally empty journal must scope its query to its own place ids. The functional suite already does.
- `ExportEventModel.xid` is a `UserDefinedType`; `alembic autogenerate` logs that it cannot reflect `XID8`. If a future migration autogenerates a type change for `xid`, discard it.

---

## Self-Check: PASSED
