---
phase: 15-acceslibre-round-trip
plan: 01
subsystem: export
tags: [export, lov2_partner, licence-matrix, zip, typer, postgresql]

requires:
  - phase: 14-open-odbl-export
    provides: the snapshot/delta export machinery, the seven CSV entries and latest.json
  - phase: 12-licence-provenance
    provides: the reviewed licence matrix and its SQL twin (_licence_allows)

provides:
  - export_odbl(..., destination="open_export") and _write_zip(..., destination=...) — no DESTINATION constant
  - admin export odbl --destination {open_export|lov2_partner}, full snapshots only
  - partner archive naming that never collides with an ODbL snapshot
  - functional proof that the licence gate keeps odbl/cdla rows out of the feed and counts them

affects: [15-03 lov2 projection, 15-04 push + build_lov2_feed, 15-05 dual licence]

actuals:
  tokens: 2878
  tasks: 2
  commits: 2
  plan_head_before: 7dfe7dcc7d41547b15a3f9d2daaa9a92c94c1584
  plan_head_after: b1894de0dffac71cae581f84129ceb0a6f80a578

tech-stack:
  added: []
  patterns:
    - "destination is a use-case parameter, never a module constant"
    - "archive stem derives from the destination; the ODbL names stay unchanged"
    - "partner feeds are full snapshots only, refused fail-fast on delta/since"

key-files:
  created:
    - tests/functional/places/test_lov2_export.py
  modified:
    - src/letmegetin/application/places/export.py
    - src/letmegetin/admin.py

key-decisions:
  - "Partner archives are named lov2_partner-<stamp>-full.zip so a glob of export-*-full.zip never picks one up (CONTEXT: naming is agent's discretion)"
  - "A non-open_export destination with --delta/--since raises DomainError: the shared journal prune makes a partner delta chain unsafe until one is specified"
  - "Task 2's identifier-rule fixture was not written: the rule CSV and its projection arrive in 15-03/15-04, so there is nothing to pin at wave 1"

patterns-established:
  - "Destination threading: export_odbl -> _write_zip -> stream_* (destination), one predicate for every destination"
  - "Directory separation: the served route reads settings.export_dir only; the operator's --out is proof-tested to stay unserved"

requirements-completed: [PART-01]

coverage:
  - id: D1
    description: "admin export odbl --destination lov2_partner writes a snapshot ZIP + latest.json to the operator-chosen --out, and the public /api/v1/export routes never serve it or touch the ODbL index"
    requirement: PART-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_lov2_export.py#test_partner_archive_is_written_to_out_and_never_served"
        status: pass
      - kind: other
        ref: "uv run ruff check . && uv run ruff format --check . && uv run mypy"
        status: pass
    human_judgment: false
  - id: D2
    description: "Only matrix-allowed rows reach the lov2 feed; odbl and cdla rows are absent and counted in the manifest per source and licence"
    requirement: PART-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_lov2_export.py#test_lov2_feed_excludes_odbl_and_cdla"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_export.py (the ODbL path stays green: 9 tests)"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-11-15
status: complete
---

# Phase 15 Plan 01: AccesLibre round trip Summary

**The Phase 14 export is now destination-parameterised, and `--destination lov2_partner` writes a licence-gated partner archive to an operator-chosen directory the public ODbL route cannot serve.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-11-15T18:08:31Z
- **Completed:** 2026-11-15T18:11:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `export_odbl` and `_write_zip` take a `destination`; the `DESTINATION` module constant is gone (5 read sites threaded).
- `admin export odbl --destination lov2_partner --out <dir>` produces a real snapshot ZIP + `latest.json` in that directory, named `lov2_partner-<stamp>-full.zip` so it can never collide with an ODbL snapshot.
- A non-`open_export` destination refuses `--delta`/`--since` fail-fast — the shared journal prune makes a partner delta chain unsafe until one is specified.
- The licence gate is proven end-to-end: `lov2` rows ship, `odbl` and `cdla` rows are absent from `places.csv` and counted in `manifest.excluded_places` per source and licence (no silent drop).
- The public `/api/v1/export/{partner}.zip` returns 404 and `/api/v1/export/latest.json` still serves the pre-existing ODbL index, with `settings.export_dir` untouched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Parameterise the export destination and separate the partner directory** - `f98ef8a` (feat)
2. **Task 2: The licence gate — odbl/cdla rows never reach the feed and are counted** - `b1894de` (test)

**Plan metadata:** see the close-out commit that carries this SUMMARY.

## Files Created/Modified

- `src/letmegetin/application/places/export.py` — `destination` threaded through `export_odbl`/`_write_zip`, delta guard, per-destination archive stem
- `src/letmegetin/admin.py` — `--destination` option on `export odbl`
- `tests/functional/places/test_lov2_export.py` — the not-served proof and the licence-gate proof

## Decisions Made

- **Partner archive naming:** `lov2_partner-<stamp>-full.zip`. The ODbL names (`export-*-full.zip`, `delta-*.zip`) are unchanged, so every existing consumer glob still matches and 14's committed expectations stay valid.
- **Deltas are refused for a partner destination**, with the plan's message: the journal prune is shared, so a partner delta chain would need its own contract first.
- **`_write_zip(destination=...)` is keyword-with-default**, so 15-04 can add `headers` beside it without another call-site rewrite.

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 3 - Blocking] Task 2's identifier-rule fixture was not written**
- **Found during:** Task 2 (licence gate test)
- **Issue:** Task 2 asks the fixture to inject an `origin_id` identifier rule "because the committed default is `blocked;UNVERIFIED`". Neither `data/referential/acceslibre_identifier_rule.csv` nor `resolve_identifier`/the lov2 projection exists yet — 15-03 creates the CSV and the probe, 15-04 wires the projection into the feed. There was nothing to pin.
- **Fix:** The licence gate test seeds the three source licences directly (lov2 via `acceslibre`, plus test sources mapped to `odbl` and `cdla`) and asserts on the feed and the manifest. The default-`blocked` behaviour stays 15-04's test, as the plan itself says.
- **Verification:** `uv run pytest tests/functional/places/test_lov2_export.py -m functional -x` → 2 passed.
- **Committed in:** `b1894de`

**2. [Deviation - Naming] Partner archive stem**
- **Found during:** Task 1
- **Issue:** D-04 says "the same ZIP machinery … the only differences are the licence predicate and the archive name", without naming the archive.
- **Fix:** The stem is the destination for a non-ODbL destination (`lov2_partner-…`); `open_export` keeps `export-…` exactly as before.
- **Verification:** the not-served test asserts the `lov2_partner-*` name; the ODbL suite (9 tests) still passes unchanged.
- **Committed in:** `f98ef8a`

---

**Total deviations:** 1 auto-adjusted (blocking dependency on a later wave), 1 naming choice within the plan's stated discretion.
**Impact on plan:** No scope creep; neither deviation changes a deliverable. 15-04 must add the identifier-rule test it owns.

## Issues Encountered

- The GitNexus index was 41 commits behind HEAD; `impact` on `export_odbl` and `_write_zip` still returned `risk: LOW, epistemic: exact` with only `admin.py`'s callback as a caller, which matches the source read, so no reindex was needed. Post-commit `detect_changes --scope compare --base-ref main` reported only the intended symbols (`export_odbl`, `_write_zip`, `export_odbl_command` + its callback) and the four export processes covered by `test_export.py`.
- `.planning/STATE.md` and `.planning/state.json` were already modified when this executor started; they are carried by the close-out commit, not by a task commit.

## User Setup Required

None - no external service configuration required. No dependency was added.

## Next Phase Readiness

- 15-03 can build the projection on `export_odbl(destination=…)` and 15-04's `build_lov2_feed` can call `_write_zip(destination=…, headers=…)` without touching the ODbL call site.
- The `dual` licence (15-05) needs no code change here: the feed reads the matrix, so adding `dual;lov2_partner;true` widens the feed by data alone.

## Self-Check: PASSED
