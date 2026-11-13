---
phase: 12-licence-provenance
plan: 01
subsystem: database
tags: [postgres, alembic, sqlalchemy, licensing, odbl, etalab, backfill]

# Dependency graph
requires:
  - phase: 10-dataset-import
    provides: place / place_accessibility rows whose value JSONB already carries the source
provides:
  - provenance columns on place (source_license, source_url, retrieved_at, observed_at)
  - provenance columns on place_accessibility (source, source_license, observed_at, recorded_at, actor)
  - licence, licence_destination, source_licence and place_accessibility_write tables
  - reviewed CSVs data/referential/{licences,licence_destinations,source_licences}.csv
  - a batched, fail-closed D-04 backfill driven by source_licences.csv
affects: [12-02 write path, 12-03 licence admin, 12-04 enforcement predicate, 12-05 conflict rules, 14 export, 15 AccesLibre round trip]

actuals:
  tokens: 6453
  tasks: 3
  commits: 3
  plan_head_before: fa40d792aeda2d7f17b05630d00fbcb56de77ff8
  plan_head_after: 2f82bc2

tech-stack:
  added: []
  patterns:
    - "Provenance as dedicated columns (D-01), never inside the value JSONB"
    - "Reviewed CSV drives the data: source_licences.csv resolves source -> licence, in the migration and later in the write path (LIC-05)"
    - "Fail-closed bulk backfill: batched UPDATE, then raise if any row is left without a licence"

key-files:
  created:
    - migrations/versions/0011_licence_provenance.py
    - data/referential/licences.csv
    - data/referential/licence_destinations.csv
    - data/referential/source_licences.csv
    - tests/functional/places/test_provenance.py
  modified:
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/domain/places/entities.py
    - src/letmegetin/infrastructure/persistence/mappers.py
    - tests/functional/places/test_places_search.py
    - tests/functional/places/test_places_reviews.py

key-decisions:
  - "The two operator-supplied effective dates are both 2026-10-26 (acceslibre->lov2, user->odbl), recorded verbatim, never guessed."
  - "licence uses its slug as primary key: the reviewed CSV names licences by slug, so a surrogate id would have no consumer."
  - "The backfill also derives place_accessibility.actor from the same data (importer:<source>, user:<user_id>) because D-03 makes the column NOT NULL and existing rows carry the attribution in nothing but their JSONB."
  - "The destination matrix allows open_export everywhere and refuses odbl/cdla towards lov2_partner, with the LIC-03 row (odbl;lov2_partner;false) as data."

patterns-established:
  - "A migration may read a reviewed CSV: migrations/versions/0011 reads data/referential/source_licences.csv with stdlib csv, so the rule stays in reviewed data, not in a CASE branch (LIC-05)."
  - "NOT NULL provenance columns are added nullable, backfilled, then ALTER ... SET NOT NULL in the same migration, so an unmapped source fails the migration instead of persisting a NULL licence."

requirements-completed: [LIC-01]

coverage:
  - id: D1
    description: "place and place_accessibility carry the provenance columns; the four licence tables exist"
    requirement: LIC-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance.py#test_backfill_resolves_every_source_from_reviewed_data"
        status: pass
      - kind: other
        ref: "uv run mypy && uv run ruff check src/letmegetin/infrastructure/persistence/models.py src/letmegetin/domain/places/entities.py src/letmegetin/infrastructure/persistence/mappers.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "the three reviewed CSVs exist and are git-versioned, carrying the operator-supplied effective_from dates"
    requirement: LIC-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance.py#test_backfill_resolves_every_source_from_reviewed_data (reads source_licences.csv, asserts the backfill used it)"
        status: pass
    human_judgment: true
    rationale: "The 3x3 destination matrix is a legal-basis judgement (which licence may leave to which destination); only the LIC-03 row was specified by the phase, the other six cells need a data review."
  - id: D3
    description: "after alembic upgrade head, zero rows carry a NULL source_license and no answer carries a NULL/empty source"
    requirement: LIC-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_provenance.py#test_backfill_resolves_every_source_from_reviewed_data"
        status: pass
      - kind: other
        ref: "LETMEGETIN_DATABASE_URL=.../letmegetin_test uv run alembic upgrade head && uv run alembic current"
        status: pass
    human_judgment: false
  - id: D4
    description: "an unmapped source fails the migration (fail-closed) instead of leaving a NULL licence"
    verification:
      - kind: manual_procedural
        ref: "inserted a place with source='overture' at 0010, ran alembic upgrade head: RuntimeError naming place.overture=1, transaction rolled back to 0010"
        status: pass
    human_judgment: true
    rationale: "No committed test asserts the raise; it was proven by hand during execution and is worth a regression test once 12-03 seeds the licence tables."

# Metrics
duration: 6min
completed: 2026-11-13
status: complete
---

# Phase 12 Plan 01: Licence provenance data model Summary

**Migration 0011 adds per-row licence provenance to places and answers, four licence tables, and a batched fail-closed backfill that resolves every existing source from the reviewed `source_licences.csv` instead of a code branch.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-11-13T11:58:34Z
- **Completed:** 2026-11-13T12:03:36Z
- **Tasks:** 3 executed (Task 2 was the operator checkpoint, satisfied before dispatch)
- **Files modified:** 10

## Accomplishments

- `place` carries `source_license`, `source_url`, `retrieved_at`, `observed_at`; `place_accessibility` carries `source`, `source_license`, `observed_at`, `recorded_at`, `actor` — schema, domain entities and mappers all agree (`alembic check` shows no drift beyond PostGIS's `spatial_ref_sys`).
- Four new tables: `licence`, `licence_destination` (with the `destination IN (...)` check), `source_licence` (the effective-dated correspondence) and `place_accessibility_write` (the D-12 journal, `decision`/`reason` checks, `reason` nullable for an accepted write).
- Migration `0011` backfills every pre-existing row in batches: answers take `source` from `value->>'source'`, `actor` from `importer:<source>` / `user:<user_id>`, and licences come from `source_licences.csv`; any row left unlicensed raises and rolls the migration back.
- Three reviewed CSVs under git: `licences.csv` (lov2, odbl, cdla), `licence_destinations.csv` (the full 3×3 matrix including `odbl;lov2_partner;false`) and `source_licences.csv` with the operator's dates, both **2026-10-26**.
- `tests/functional/places/test_provenance.py` seeds rows at the 0010 schema, upgrades, and asserts the licences match the reviewed CSV it reads itself — so a hard-coded `CASE` with a divergent value would fail.

## Task Commits

Each task was committed atomically:

1. **Task 1: Provenance columns + four new tables (models, entities, mappers)** — `d8c05c7` (feat)
2. **Task 2: Operator supplies the effective dates** — checkpoint, satisfied before dispatch (`acceslibre` and `user` → 2026-10-26); recorded in commit 3
3. **Task 3: Migration 0011 + the three reviewed CSVs** — `ab67f50` (feat)
4. **Task 4: Functional test of the backfill** — `2f82bc2` (test)

**Plan metadata:** committed separately after this file.

## Files Created/Modified

- `migrations/versions/0011_licence_provenance.py` — columns, four tables, batched fail-closed backfill reading the reviewed CSV
- `data/referential/licences.csv` — `slug;name;url;obligations` for lov2, odbl, cdla
- `data/referential/licence_destinations.csv` — the 3×3 `licence × destination` matrix
- `data/referential/source_licences.csv` — `acceslibre;lov2;2026-10-26`, `user;odbl;2026-10-26`
- `src/letmegetin/infrastructure/persistence/models.py` — provenance columns, `LicenceModel`, `LicenceDestinationModel`, `SourceLicenceModel`, `PlaceAccessibilityWriteModel`
- `src/letmegetin/domain/places/entities.py` — `Place` and `PlaceAccessibility` gain the same fields, all defaulting to `None`
- `src/letmegetin/infrastructure/persistence/mappers.py` — copies the fields, as `source=model.source` already did
- `tests/functional/places/test_provenance.py` — the D-04 proof
- `tests/functional/places/test_places_search.py`, `tests/functional/places/test_places_reviews.py` — fixture inserts now supply the new NOT NULL `source` / `actor`

## Decisions Made

- **Effective dates** both **2026-10-26**, supplied by the operator; recorded verbatim, no placeholder invented.
- **`licence.slug` is the primary key** rather than a surrogate id: the reviewed CSV names licences by slug and `source_licence`/`licence_destination` point at it, so an id would have no consumer.
- **`actor` backfill**: D-03 makes the column NOT NULL, and existing rows only carry attribution inside the value JSONB, so the migration derives `importer:<source>` or `user:<user_id>` from that same data (the alternative — a blanket `server_default` — would misattribute user contributions as importer writes).
- **`place_accessibility_write.reason` is nullable**: an accepted write stores `NULL`, a rejected one names why; `not_redistributable` stays reserved with no producer this phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing functional fixtures could not insert after the NOT NULL columns**
- **Found during:** Task 4 (running the suite after the migration)
- **Issue:** `place_accessibility.source` and `.actor` are NOT NULL after 0011, so the raw-SQL seeds in `test_places_search.py` and `test_places_reviews.py` raised `NotNullViolationError` and errored 20 tests.
- **Fix:** the four fixture inserts now pass `source` (`'test-search'` / `'test-p4'`) and `actor` (`'test'`); no assertion changed.
- **Files modified:** `tests/functional/places/test_places_search.py`, `tests/functional/places/test_places_reviews.py`
- **Verification:** `uv run pytest tests/functional/places/test_places_search.py tests/functional/places/test_places_reviews.py -q` → 20 passed.
- **Committed in:** `2f82bc2`

**2. [Rule 3 - Blocking] The backfill needed an attribution value for pre-existing answers**
- **Found during:** Task 3 (writing the migration)
- **Issue:** `actor` is declared NOT NULL (D-03) but the plan specifies no backfill for it, so `ALTER ... SET NOT NULL` would fail on the 634k-row production table.
- **Fix:** derive `actor` from the same `value` JSONB the plan already reads for `source` (`importer:<source>`, `user:<user_id>`).
- **Files modified:** `migrations/versions/0011_licence_provenance.py`
- **Verification:** manual round-trip showed `importer:acceslibre` and `user:42` on the seeded rows; `test_provenance.py` asserts `user:4242`.
- **Committed in:** `ab67f50`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both were required for the migration to apply and for the suite to reach the write-path boundary. No scope creep: the write path itself is untouched (12-02 owns it).

## Issues Encountered

- **Five functional tests are red until 12-02 rewrites the write path.** `upsert_accessibility` still inserts only `(place_id, criterion_id, value)`, so `source` and `actor` violate NOT NULL. Failing today:
  `tests/functional/places/test_places_import.py::test_acceslibre_import_writes_accessibility_values_and_photos`,
  `tests/functional/places/test_places_duplicates.py::test_coverage_csv_counts_places_by_category_and_country` (which imports first), and the three `tests/functional/accounts/test_auth_contribution.py` cases. Everything else passes (282 passed, 5 failed).
  This is the plan's stated sequence — 12-02 owns the write path — but 12-02 must close these before the phase verifies.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- 12-02 can build the ownership/freshness/write-journal rewrite on `upsert_accessibility`; the columns and `place_accessibility_write` already exist.
- 12-03 can seed `licence` / `licence_destination` / `source_licence` from the three CSVs; the backfill already reads `source_licences.csv` so both paths share one mapping.
- No committed test asserts the fail-closed raise (verified by hand) — worth a regression test once 12-03 can seed an unmapped-source scenario.

---

## Self-Check: PASSED
