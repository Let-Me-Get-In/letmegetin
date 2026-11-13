---
phase: 12-licence-provenance
plan: 02
subsystem: places
tags: [provenance, licensing, odbl, lov2, fastapi, sqlalchemy, acceslibre]

# Dependency graph
requires:
  - phase: 12-licence-provenance
    plan: 01
    provides: provenance columns, source_licence table, Place/PlaceAccessibility entities and mappers
provides:
  - upsert_accessibility carries source/actor/observed_at and resolves source_license from source_licence
  - place add/update snapshot source_license plus source_url/retrieved_at/observed_at
  - AccesLibre import maps date_maj to observed_at and stamps importer:acceslibre
  - contribute stamps source=user, actor=user:<id>, odbl licence
  - PlaceDetailOut/AccessibilityValueOut expose source, license, observed_at
  - docs/public-api.md provenance section and regenerated docs/openapi.json
affects: [12-03 licence seed, 12-04 enforcement predicate, 12-05 conflict rules, 13 record UI]

actuals:
  tokens: 7676
  tasks: 2
  commits: 2
  plan_head_before: 5d3d3fcecf3a27691860b85c9a05cf70cf21ae52
  plan_head_after: f5422f61e66833ce6b838d85c8369134f1df6f44

tech-stack:
  added: []
  patterns:
    - "The repository resolves the licence at write time from source_licence; no caller carries a licence literal (LIC-05)"
    - "Fail-closed resolution: an unmapped source raises DomainError instead of persisting a NULL licence (D-15)"
    - "Provenance dates are naive UTC in the database (asyncpg rejects aware datetimes for timestamp columns)"
    - "A functional autouse fixture loads the reviewed source_licence rows, so no suite depends on the 12-03 seed"

key-files:
  created:
    - tests/functional/places/test_provenance_write.py
    - tests/functional/places/test_provenance_read.py
  modified:
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/application/places/import_acceslibre.py
    - src/letmegetin/application/places/contribute.py
    - src/letmegetin/api/schemas/places.py
    - docs/public-api.md
    - docs/openapi.json
    - tests/db.py
    - tests/functional/conftest.py

key-decisions:
  - "One shared write path: the repository resolves source_license with a single SELECT (effective_from <= now(), newest first); both callers only pass source/actor/observed_at."
  - "update() keeps an existing non-NULL source_license instead of re-resolving it, so a source re-licensing never restates an existing copy (D-07)."
  - "Provenance timestamps are stored as naive UTC: every provenance column is timestamp without time zone and asyncpg rejects aware datetimes; a date_maj with an offset is converted to UTC first."
  - "The functional suite seeds licence/source_licence from data/referential/source_licences.csv in an autouse fixture, so the write path is testable before 12-03 ships admin licences sync."

patterns-established:
  - "Provenance is resolved where the write happens: a caller names the source and actor, the repository owns the source -> licence lookup."
  - "A read schema field named license maps from the model's source_license in the from_* classmethod, never in the endpoint."

requirements-completed: [LIC-01]

coverage:
  - id: D1
    description: "every answer write stamps source, resolved licence, observed_at, recorded_at and actor; an unmapped source fails closed"
    requirement: LIC-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance_write.py#test_an_acceslibre_write_takes_its_licence_from_the_reviewed_table"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_provenance_write.py#test_a_contribution_carries_the_user_licence_never_none"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_provenance_write.py#test_an_unmapped_source_fails_closed"
        status: pass
    human_judgment: false
  - id: D2
    description: "a newly imported place carries its licence, a retrieval timestamp and the source's claimed date (date_maj), NULL when absent"
    requirement: LIC-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance_write.py#test_an_import_stamps_licence_retrieval_and_the_source_claimed_date"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_provenance_write.py#test_an_empty_export_date_leaves_observed_at_null"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /api/v1/places/{slug} returns source, license and observed_at on the place and on every answer; the search list is unchanged"
    requirement: LIC-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance_read.py#test_the_detail_endpoint_surfaces_provenance_on_the_place_and_each_answer"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_provenance_read.py#test_the_search_list_carries_no_provenance_per_result"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/openapi.json regenerates deterministically from the app"
    verification:
      - kind: other
        ref: "uv run python scripts/export_openapi.py twice -> byte-identical docs/openapi.json"
        status: pass
    human_judgment: false
  - id: D5
    description: "docs/public-api.md documents the additive provenance fields and that observed_at is the source's claim, not ingestion time"
    verification:
      - kind: other
        ref: "docs/public-api.md section 'Provenance'"
        status: pass
    human_judgment: true
    rationale: "Whether the published wording is clear enough for a partner is an editorial judgement no test asserts."

# Metrics
duration: 13min
completed: 2026-11-13
status: complete
---

# Phase 12 Plan 02: Licence provenance write → read path Summary

**The provenance tracer slice is proven end to end: an AccesLibre import and a user contribution both snapshot their licence from the reviewed `source_licence` table, and `GET /api/v1/places/{slug}` returns `source`, `license` and `observed_at` on the place and on every answer, with the place date being AccesLibre's `date_maj`.**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-11-13T11:59:00Z
- **Completed:** 2026-11-13T12:12:30Z
- **Tasks:** 2 executed
- **Files modified:** 11 (2 created, 9 modified)

## Accomplishments

- `upsert_accessibility` now takes `source`, `actor` and `observed_at`; the SQLAlchemy repository resolves `source_license` with one `SELECT licence_slug FROM source_licence WHERE source = :source AND effective_from <= now()` and raises `DomainError` when the source is unmapped — no caller passes a licence, and the `source_license` column is the write-time snapshot.
- `SqlAlchemyPlaceRepository.add`/`update` stamp the same licence on the place, plus `source_url`/`retrieved_at`/`observed_at` taken from the entity; `update` only resolves a licence when the row has none, so a re-licensing source cannot restate an existing copy.
- The AccesLibre importer maps `date_maj` (aliases `date_mise_a_jour`, `updated_at`) onto a new `AcceslibreRow.observed_at` through a `_date` helper, sets `place.retrieved_at` at import time, and passes `importer:acceslibre` down to the answer write. `accessibility_values` is untouched: provenance lives in columns, not the JSONB.
- `contribute` passes `source="user"`, `actor=f"user:{user.id}"`, `observed_at=None`; the licence resolves to `odbl`, matching the D-04 backfill.
- `PlaceDetailOut` and `AccessibilityValueOut` expose `source`, `license`, `observed_at`; the place-level date maps from `place.observed_at` (`date_maj`), never `retrieved_at`, which stays internal. `PlaceSummaryOut` (search) is unchanged.
- `docs/public-api.md` gains a Provenance section and the endpoint table row; `docs/openapi.json` was regenerated with `scripts/export_openapi.py` and is byte-identical across two runs.
- **The five functional tests that were red after 12-01 are green:** the import accessibility test, the coverage CSV test and the three contribution tests all pass through the new write path (full suite: 294 passed).

## Task Commits

Each task was committed atomically:

1. **Task 1: Stamp provenance on the write path, licence resolved from `source_licence`** — `5895636` (feat)
2. **Task 2: Surface provenance on the detail endpoint + public contract** — `f5422f6` (feat)

**Plan metadata:** committed separately after this file.

## Files Created/Modified

- `src/letmegetin/domain/places/repositories.py` — `upsert_accessibility` port carries `source`/`actor`/`observed_at`
- `src/letmegetin/infrastructure/persistence/repositories.py` — `_source_licence` resolver, provenance-stamping upsert, place `add`/`update`
- `src/letmegetin/application/places/import_acceslibre.py` — `observed_at` mapping and parsing, `retrieved_at`, importer actor
- `src/letmegetin/application/places/contribute.py` — explicit `user` provenance
- `src/letmegetin/api/schemas/places.py` — provenance fields on the detail and answer schemas
- `docs/public-api.md` — Provenance section, endpoint row
- `docs/openapi.json` — regenerated
- `tests/db.py` — `seed_source_licences()` reading the reviewed CSV
- `tests/functional/conftest.py` — autouse fixture that seeds it
- `tests/functional/places/test_provenance_write.py` — the five write-path behaviours
- `tests/functional/places/test_provenance_read.py` — the detail/search tracer

## Decisions Made

- **Resolution lives in the repository, not the callers.** One `SELECT` on `source_licence`, `effective_from <= now()`, newest first; both callers name only `source`/`actor`/`observed_at`. This is the seam 12-05 extends with conflict rules without touching the signature again.
- **`update()` does not re-resolve an existing licence** (`model.source_license or await ...`): D-07 says a copy keeps the licence it was taken under, so re-resolving on update would restate an existing row's terms.
- **Naive UTC timestamps.** All provenance columns are `timestamp without time zone` and asyncpg rejects aware datetimes (verified), so `_date` converts an offset to UTC and drops `tzinfo`, and `retrieved_at` is `datetime.now(UTC).replace(tzinfo=None)`.
- **Tests own the reviewed rows.** The write path needs `source_licence` rows that 12-03's seed will load in production, so `tests/db.py` reads `data/referential/source_licences.csv` and the functional suite seeds it per test — data-driven, no literal, and the swap test proves the resolution really reads the table.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing functional suites needed reviewed `source_licence` rows**
- **Found during:** Task 1 (first full functional run after the write path started failing closed)
- **Issue:** `upsert_accessibility` now raises `DomainError` for an unmapped source, and the test database holds no `source_licence` rows until 12-03's seed exists, so every import and contribution test would have failed for a reason unrelated to what it asserts.
- **Fix:** added `seed_source_licences()` in `tests/db.py` (reads `data/referential/source_licences.csv`, inserts `licence` and `source_licence` idempotently) and an autouse fixture in `tests/functional/conftest.py` that applies it.
- **Files modified:** `tests/db.py`, `tests/functional/conftest.py`
- **Verification:** `uv run pytest -m functional` → 73 passed (was 5 failed, 63 passed before the plan).
- **Committed in:** `5895636`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Test infrastructure only — the production write path and the plan's contract are exactly as planned. The fixture becomes redundant but harmless once 12-03 loads the catalogue in the seed.

## Issues Encountered

- None outstanding. The five functional tests left red by 12-01 now pass.
- **Operational note for 12-03:** the development database still has no `source_licence` rows, so `letmegetin-admin import acceslibre` fails closed with a `DomainError` naming the source until `admin licences sync` runs. That is the intended D-15 behaviour, not a regression.

## Threat Flags

None — the response additions are read-only and additive; the contribution provenance is derived server-side (`source="user"`, `actor=f"user:<id>"`), so a client cannot mass-assign it (T-12-02).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The `upsert_accessibility` signature is final for 12-05 to add ownership (`other_source`), freshness (`stale`) and the `place_accessibility_write` journal behind it without an architectural change.
- 12-03 must load `licence` and `source_licence` in the seed **before** any import; `admin licences sync` fills exactly the rows the write path resolves.
- `place.source_url` remains NULL for AccesLibre until a real URL column is confirmed in the export (no alias was invented).

---

## Self-Check: PASSED
