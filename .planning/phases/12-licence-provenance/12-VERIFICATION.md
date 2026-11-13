---
phase: 12-licence-provenance
verified: 2026-11-13T12:38:44Z
status: passed
score: 22/22 must-haves verified
covered_files:
  - .planning/phases/12-licence-provenance/12-01-PLAN.md
  - .planning/phases/12-licence-provenance/12-01-SUMMARY.md
  - .planning/phases/12-licence-provenance/12-02-PLAN.md
  - .planning/phases/12-licence-provenance/12-02-SUMMARY.md
  - .planning/phases/12-licence-provenance/12-03-PLAN.md
  - .planning/phases/12-licence-provenance/12-03-SUMMARY.md
  - .planning/phases/12-licence-provenance/12-04-PLAN.md
  - .planning/phases/12-licence-provenance/12-04-SUMMARY.md
  - .planning/phases/12-licence-provenance/12-05-PLAN.md
  - .planning/phases/12-licence-provenance/12-05-SUMMARY.md
  - data/referential/licence_destinations.csv
  - data/referential/licences.csv
  - data/referential/source_licences.csv
  - docs/openapi.json
  - docs/public-api.md
  - migrations/versions/0011_licence_provenance.py
  - src/letmegetin/admin.py
  - src/letmegetin/api/schemas/places.py
  - src/letmegetin/application/places/contribute.py
  - src/letmegetin/application/places/import_acceslibre.py
  - src/letmegetin/application/referential/licences.py
  - src/letmegetin/domain/places/entities.py
  - src/letmegetin/domain/places/licence.py
  - src/letmegetin/domain/places/repositories.py
  - src/letmegetin/domain/referential/entities.py
  - src/letmegetin/domain/referential/repositories.py
  - src/letmegetin/infrastructure/persistence/licence_repositories.py
  - src/letmegetin/infrastructure/persistence/mappers.py
  - src/letmegetin/infrastructure/persistence/models.py
  - src/letmegetin/infrastructure/persistence/repositories.py
  - src/letmegetin/seed.py
  - tests/db.py
  - tests/functional/conftest.py
  - tests/functional/places/test_places_reviews.py
  - tests/functional/places/test_places_search.py
  - tests/functional/places/test_provenance.py
  - tests/functional/places/test_provenance_conflict.py
  - tests/functional/places/test_provenance_read.py
  - tests/functional/places/test_provenance_write.py
  - tests/functional/places/test_redistribution.py
  - tests/functional/referential/test_admin_cli.py
  - tests/integration/referential/test_seed_vocabulary.py
  - tests/unit/application/referential/fakes.py
  - tests/unit/application/referential/test_licences.py
  - tests/unit/domain/places/test_licence.py
  - tests/unit/test_seed.py
covered_digest: "v4:sha256:c003a92160e285310155ab1031898e8d2910d3935a4e576b66e84446d0e72359"
behavior_unverified: 0
overrides_applied: 0
human_verification_completed: 2026-11-13
human_verification:
  - test: "Review the six redistribution-matrix cells the phase did not specify — `odbl × open_export`, `odbl × osm`, `lov2 × {open_export,osm,lov2_partner}`, `cdla × {open_export,osm}`, plus `cdla × lov2_partner` (currently denied) — against the obligations in `data/referential/licences.csv`, and decide the `user → odbl` / `lov2_partner` question before PART-01 ships a feed."
    expected: "Every cell is either confirmed as the intended legal posture or changed in `data/referential/licence_destinations.csv` (then `admin licences sync`). Until then `admin licences audit` treats the cells as authoritative rules."
    why_human: "Whether an ODbL/Etalab/CDLA row may leave towards a partner or OSM is a legal judgement, not a code property. The phase specified only `odbl × lov2_partner = false` (LIC-03); 12-01's own coverage records `human_judgment: true` for the remaining cells and 12-03 flags them 'for human legal review'. No tool in this repo can decide it."
    owner: "LET-79 / PART-01 review before Phase 14 export"
---

# Phase 12: Licence provenance Verification Report

**Phase Goal:** Every place and every answer records where it came from and under what licence, and the system enforces what can flow to which destination.
**Verified:** 2026-11-13T12:38:44Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After `alembic upgrade head`, no pre-existing place or answer is left with a NULL `source_license`, and the backfill resolves each source from `data/referential/source_licences.csv` rather than a code branch (LIC-01, D-04) | ✓ VERIFIED | `tests/functional/places/test_provenance.py` seeds rows at 0010, upgrades, asserts the mapping read from the same CSV and `count(*) WHERE source_license IS NULL = 0` on both tables — re-ran: passed. The migration reads the CSV with stdlib `csv` (`_reviewed_mapping`) |
| 2 | An existing source with no reviewed mapping fails the migration with a named error instead of persisting a NULL licence (D-15) | ✓ VERIFIED | Observed directly: downgraded to 0010, inserted `place(source='overture')`, `alembic upgrade head` raised `RuntimeError: licence backfill left rows without a licence: place.overture=1` and the transaction stayed at 0010; row removed, re-upgraded to `0011 (head)` |
| 3 | `place` carries `source_license`, `source_url`, `retrieved_at`, `observed_at`; `place_accessibility` carries `source`, `source_license`, `observed_at`, `recorded_at`, `actor` (D-01/D-02) | ✓ VERIFIED | Migration `0011`, `models.py:255-259,316-320`, `entities.py:55-77`, `mappers.py:69-110`; `alembic check` reports only the known PostGIS `spatial_ref_sys` noise, no model drift |
| 4 | A newly imported AccesLibre place gets a non-NULL licence resolved from `source_licence`, plus `retrieved_at` and the export's `date_maj` as `observed_at`; a blank date stays NULL (LIC-01) | ✓ VERIFIED | `test_provenance_write.py::test_an_import_stamps_licence_retrieval_and_the_source_claimed_date`, `::test_an_empty_export_date_leaves_observed_at_null`; `import_acceslibre.py:283-284` |
| 5 | Every answer write stamps `source`, `source_license`, `observed_at`, `recorded_at`, `actor`; the licence is resolved from `source_licence` at write time, and an unmapped source raises instead of writing a NULL (LIC-01/LIC-05, D-07/D-15) | ✓ VERIFIED | `upsert_accessibility` → `_source_licence` (`repositories.py:732-748,921-1013`); `test_an_acceslibre_write_takes_its_licence_from_the_reviewed_table` swaps the mapping row and observes the snapshot change; `test_an_unmapped_source_fails_closed` |
| 6 | `contribute` stamps `source='user'`, `actor='user:<id>'` and the `odbl` licence resolved from reviewed data — never `None` (LIC-01) | ✓ VERIFIED | `contribute.py:34-37`; `test_a_contribution_carries_the_user_licence_never_none` |
| 7 | `GET /api/v1/places/{slug}` exposes `source`, `license`, `observed_at` on the place and on every answer; the place value is the source's `date_maj`, not the ingestion time (D-16) | ✓ VERIFIED | `schemas/places.py:44-47,148-192`; `test_provenance_read.py::test_the_detail_endpoint_surfaces_provenance_on_the_place_and_each_answer` |
| 8 | `GET /api/v1/places` is unchanged — no provenance per search result (D-17) | ✓ VERIFIED | `test_the_search_list_carries_no_provenance_per_result`; `PlaceSummaryOut` in the regenerated OpenAPI has only the eight pre-existing keys |
| 9 | The public contract matches the endpoint: `docs/public-api.md` documents the three fields and `docs/openapi.json` is byte-identical to the app | ✓ VERIFIED | Ran `uv run python scripts/export_openapi.py` → `git diff docs/openapi.json` empty; `PlaceDetailOut` and `AccessibilityValueOut` carry `source`/`license`/`observed_at` |
| 10 | The catalogue, the redistribution matrix and the source mapping live in three git-reviewed CSVs loaded by the seed and the CLI; no licence mapping or rule literal hides in source (LIC-05) | ✓ VERIFIED | `data/referential/{licences,licence_destinations,source_licences}.csv`; `application/referential/licences.py` loaders; `grep lov2\|odbl\|cdla src/` returns only the closed `DESTINATIONS` set, docstrings and a CLI help string |
| 11 | `admin licences sync` loads all three CSVs idempotently and bumps `referential_version`; `admin licences audit` exits 0 on a complete matrix and 1 on a gap (D-08) | ✓ VERIFIED | Ran `licences sync` → `created=0 updated=0 unchanged=14`, version 1033→1034; `licences audit` → exit 0. `test_licences_audit_names_the_licence_that_lost_a_matrix_row` deletes a row → exit 1 and names it |
| 12 | `admin licences matrix` renders the matrix with the LIC-03 row denied | ✓ VERIFIED | Ran it: `lov2_partner odbl denied OSM-derived never to a lov2 destination (LIC-03)`; `test_licences_matrix_shows_the_lic03_row` |
| 13 | `can_redistribute` refuses a NULL licence, an unknown licence, a pair absent from the matrix and an absent matrix (D-15) | ✓ VERIFIED | `domain/places/licence.py:18-33`; `tests/unit/domain/places/test_licence.py` (matrix read from the reviewed CSV) |
| 14 | The SQL twin yields the same verdict as the domain predicate for every reviewed (licence, destination) pair, and a NULL or unknown licence matches no destination (D-13) | ✓ VERIFIED | `test_redistribution.py::test_the_sql_twin_agrees_with_the_domain_predicate_on_every_matrix_row` loops the whole DB matrix comparing `allowed()`, `can_redistribute()` and `redistributable_place_ids()`; `test_a_null_or_unknown_licence_matches_no_destination` |
| 15 | `odbl × lov2_partner = false` exists as a `licence_destination` row and is provable from the database alone (LIC-03) | ✓ VERIFIED | Queried `licence_destination WHERE allowed = false` → `('odbl','lov2_partner',false,'OSM-derived never to a lov2 destination (LIC-03)')`; `test_the_lic03_row_keeps_odbl_rows_out_of_a_lov2_destination` |
| 16 | Excluded rows are counted per source/licence and listable by id, and a destination typo exits 1 (D-14 operator surface) | ✓ VERIFIED | `licence_repositories.py:179-200`; `test_the_manifest_counts_excluded_rows_per_source_and_licence`, `test_the_operator_lists_the_excluded_ids_for_a_destination` (incl. unknown destination → exit 1) |
| 17 | A re-import cannot overwrite a user contribution or another source's answer; a contribution takes ownership of the row (LIC-04, D-09) | ✓ VERIFIED | `_rejection` (`repositories.py:334-353`); conflict suite proves it directly and end-to-end through `import_acceslibre` + `contribute` (`test_a_reimport_cannot_revert_a_contribution`, `test_an_import_cannot_overwrite_a_user_row`, `test_a_contribution_takes_ownership_from_another_source`) |
| 18 | Same-source replacement requires incoming `observed_at` ≥ current; every NULL combination is defined; an older file and a NULL incoming claim are rejected `stale`; a same-file replay stays idempotent (D-10) | ✓ VERIFIED | Parametrized 6-case matrix (`test_same_source_freshness_treats_null_as_the_oldest`), plus importer-level `test_an_older_file_is_rejected_as_stale`, `test_an_incoming_null_observed_at_is_rejected_as_stale`, `test_replaying_the_same_file_keeps_the_value_and_journals_each_attempt` |
| 19 | An import inserts a criterion absent on a place owned by another source without overwriting the owned one (D-11) | ✓ VERIFIED | `test_an_import_inserts_a_missing_criterion_without_overwriting_the_owned_one` |
| 20 | Every attempted answer write appends a `place_accessibility_write` row with `decision`, `reason` and the losing value (D-12) | ✓ VERIFIED | Journal insert at `repositories.py:993-994`; every conflict test asserts the journal row, including the rejected value payload |
| 21 | The application layer reaches licence data only through the `LicenceRepository` port; SQLAlchemy stays in infrastructure (DDD) | ✓ VERIFIED | `application/referential/licences.py` imports only `domain/referential/*`; `SqlAlchemyLicenceRepository` in `infrastructure/`, constructed in `admin.py` and `seed.py` |
| 22 | The seed loads catalogue, matrix and source mapping, so a fresh database holds the reviewed rows before an import resolves a licence (D-05, seed order) | ✓ VERIFIED | `seed.py:140-153,247-248`; `tests/integration/referential/test_seed_vocabulary.py::test_seed_loads_the_reviewed_licence_data`; wiring test `tests/unit/test_seed.py` |

**Score:** 22/22 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `migrations/versions/0011_licence_provenance.py` | columns, four tables, batched fail-closed backfill | ✓ VERIFIED | runs up and down; backfill proven against pre-0011 data |
| `data/referential/licences.csv` | reviewed catalogue | ✓ VERIFIED | lov2, odbl, cdla with obligations |
| `data/referential/licence_destinations.csv` | reviewed per-pair matrix | ✓ VERIFIED | 9 rows, `odbl;lov2_partner;false` present |
| `data/referential/source_licences.csv` | reviewed source → licence with effective date | ✓ VERIFIED | `acceslibre;lov2`, `user;odbl`, both `2026-10-26` |
| `src/letmegetin/domain/places/licence.py` | pure fail-closed predicate | ✓ VERIFIED | wired into tests only until Phase 14 (see Info) |
| `src/letmegetin/infrastructure/persistence/licence_repositories.py` | port implementation + SQL twin + manifest | ✓ VERIFIED | used by `admin licences`, `seed`, tests |
| `src/letmegetin/application/referential/licences.py` | loaders, sync, audit, matrix | ✓ VERIFIED | no ORM import; drives CLI and seed |
| `src/letmegetin/admin.py` | `licences sync\|matrix\|audit\|excluded` | ✓ VERIFIED | all four run; exit codes as specified |
| `src/letmegetin/seed.py` | load licence data before imports | ✓ VERIFIED | called before families/grid rebuild |
| `src/letmegetin/infrastructure/persistence/repositories.py` | one provenance-aware write path | ✓ VERIFIED | only answer writer in `src/` |
| `src/letmegetin/application/places/{contribute,import_acceslibre}.py` | pass source/actor/observed_at, no licence literal | ✓ VERIFIED | both delegate resolution to the repository |
| `src/letmegetin/api/schemas/places.py` | additive provenance fields | ✓ VERIFIED | place + answer; search summary untouched |
| `docs/public-api.md`, `docs/openapi.json` | published contract | ✓ VERIFIED | docs section added; OpenAPI regenerates identical |
| phase test files (6) | backfill, write, read, conflict, redistribution | ✓ VERIFIED | 29 phase tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contribute.py` / `import_acceslibre.py` | `upsert_accessibility` | explicit `source`/`actor`/`observed_at` | WIRED | both callers pass all three; signature has no default source |
| `upsert_accessibility` | `source_licence` table | `_source_licence` SELECT (`effective_from <= now()`) | WIRED | table-swap test observes the snapshot change |
| `upsert_accessibility` | `place_accessibility_write` | journal insert on every attempt | WIRED | asserted in every conflict case |
| `place_accessibility` / `place` | `PlaceDetailOut` / `AccessibilityValueOut` | mappers → `from_detail` | WIRED | functional read test asserts the JSON |
| `admin licences` | `application/referential/licences.py` → `SqlAlchemyLicenceRepository` | typer callbacks | WIRED | sync/matrix/audit/excluded all exercised |
| `seed.py` | `sync_licences` | `_load_licence_data` | WIRED | integration test asserts the rows |
| `licence_destination` matrix | `can_redistribute` + `redistributable_place_ids` | reviewed rows / `_may_leave` EXISTS | WIRED | agreement proven for every pair |
| Phase 14/15–17 exit paths | `can_redistribute` / SQL twin | — | NOT YET WIRED (by design) | no export or feed exists in Phase 12; see Info |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `PlaceDetailOut.license` | `place.source_license` | `source_licence` resolution at write (DB) | Yes — asserted after a real AccesLibre import | ✓ FLOWING |
| `AccessibilityValueOut.license` / `.source` / `.observed_at` | `place_accessibility.*` | same write path, `date_maj` for `observed_at` | Yes | ✓ FLOWING |
| `PlaceDetailOut.observed_at` | `place.observed_at` | AccesLibre `date_maj` at creation | Yes | ✓ FLOWING |
| `admin licences excluded` counts | `place.source_license` × `licence_destination` | SQL join on real rows | Yes — seeded places counted per group | ✓ FLOWING |
| `can_redistribute` matrix | `licence_destination` rows | `licence_destinations.csv` via seed/sync | Yes — unit test reads the CSV itself | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase functional suites (backfill, write, read, conflict, redistribution) | `uv run pytest tests/functional/places/test_provenance*.py tests/functional/places/test_redistribution.py -q` | 29 passed | ✓ PASS |
| Whole places functional directory | `uv run pytest tests/functional/places -q` | 66 passed | ✓ PASS |
| Licence unit + CLI + seed suites | `uv run pytest tests/unit/domain/places/test_licence.py tests/unit/application/referential/test_licences.py tests/unit/application/referential/test_admin_cli.py tests/unit/test_seed.py tests/integration/referential/test_seed_vocabulary.py tests/functional/referential/test_admin_cli.py -q` | 62 passed | ✓ PASS |
| Full suite | `uv run pytest -q` | 356 passed | ✓ PASS |
| Type check | `uv run mypy` | 79 source files, no issues | ✓ PASS |
| Lint / format / security | `uv run ruff check . && uv run ruff format --check . && uv run bandit -r src -c pyproject.toml` | clean; 148 files formatted; 0 High/Medium/Low | ✓ PASS |
| Migration fail-closed on an unmapped source | downgrade 0010 → insert `source='overture'` → `alembic upgrade head` | `RuntimeError: licence backfill left rows without a licence: place.overture=1`; DB stayed at 0010 | ✓ PASS |
| CLI idempotence + version bump | `python -m letmegetin.admin licences sync` twice + `referential_version` read | `created=0 updated=0 unchanged=14`, version 1033→1034 | ✓ PASS |
| Audit gate and matrix render | `python -m letmegetin.admin licences audit` / `licences matrix` / `licences excluded --destination lov2_partner` | exit 0 / LIC-03 row `denied` / `nothing excluded` on an empty table | ✓ PASS |
| OpenAPI drift | `uv run python scripts/export_openapi.py && git diff --exit-code docs/openapi.json` | no diff | ✓ PASS |

### Probe Execution

N/A — the phase declares no probe and there is no `scripts/*/tests/probe-*.sh`.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LIC-01 | 12-01, 12-02 | Every place row records source and licence; every answer records its source | ✓ SATISFIED | backfill leaves zero NULLs (test + direct observation); new imports/contributions stamp `source`/`source_license`/`actor`/dates from reviewed data; detail endpoint exposes them |
| LIC-02 | 12-04 | A row is classifiable per destination and the rule is enforced wherever rows leave | ✓ SATISFIED (seam) | `can_redistribute` + SQL twin + `admin licences excluded`; no exit path exists in Phase 12 — Phase 14 will consume the seam (exit-point counters deferred, see Info) |
| LIC-03 | 12-03, 12-04 | An OSM-derived row is never sent to a lov2 destination | ✓ SATISFIED | `odbl × lov2_partner = false` is a reviewed row provable from `licence_destination`; the predicate and SQL twin both refuse it; an OSM source has no mapping, so an OSM import fails closed until the row is reviewed |
| LIC-04 | 12-05 | Re-import never overwrites a fresher contribution or another source's row | ✓ SATISFIED | ownership + freshness enforced in the single `upsert_accessibility`; 6-case NULL matrix, importer-level stale and replay tests, journal of losing values |
| LIC-05 | 12-01, 12-02, 12-03 | Licence rules live in reviewed data, not importer code | ✓ SATISFIED (mechanical) | three CSVs loaded by seed and `admin licences sync`, validated by the loaders and the exit-1 audit; no licence literal in `src/`. The legal correctness of six matrix cells is the human item below |

No orphaned requirements: plans declare LIC-01…LIC-05 and all five appear in `.planning/REQUIREMENTS.md` § Phase 12. `REQUIREMENTS.md` still prints `Pending`; that table is updated at phase closure, as in Phase 11 — not counted as a gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| all phase-modified files | — | No `TBD` / `FIXME` / `XXX` markers | — | Debt-marker gate clear |
| `src/letmegetin` | — | No stub returns, hardcoded empty data or placeholder handlers on the audited paths; the only answer writer is `upsert_accessibility` | — | — |
| `place.source_url` | — | Column has no producer (nullable by design; the AccesLibre export carries no URL column) | ℹ️ Info | Documented in 12-02; not a requirement |
| `place.observed_at` / `retrieved_at` | — | Set at creation; a re-import refreshes the answers but not the place's own dates | ℹ️ Info | Place licence/source stay correct; only the displayed source date can age |
| `can_redistribute` / `redistributable_place_ids` | — | No in-tree consumer until Phase 14; the SQL twin covers `place.source_license` only | ℹ️ Info | Expected seam (D-13); answers need the same join when the export lands |
| `upsert_accessibility` | 941 | An answer write whose source has no reviewed mapping raises before a journal row is written | ℹ️ Info | Fail-closed config error; D-12's `reason` enum has no value for it |
| matrix destination set | `licence.py:15`, `models.py:367` | The three destination names are a code constant + DB check, while the per-pair rules are data | ℹ️ Info | D-06 fixes the destination set; adding one is a migration by design |

### Human Verification — completed 2026-11-13

#### 1. Legal review of the reviewed matrix cells — LET-79

**Done:** the operator reviewed the cells listed below and **accepted the matrix as committed**
(`data/referential/licence_destinations.csv`), explicitly as a provisional posture: "on pourra
rechanger plus tard si besoin, il va falloir étudier ça correctement".

- `odbl × open_export`, `odbl × osm`, `lov2 × open_export`, `lov2 × osm`, `lov2 × lov2_partner`,
  `cdla × open_export`, `cdla × osm` — confirmed.
- `cdla × lov2_partner = false` — kept as conservative, though a permissive licence could be
  republished to a partner; the note in the CSV says so.
- `odbl × lov2_partner = false` (LIC-03) — kept; it also withholds `user`-stamped contributions
  from a lov2 feed, which stays deferred to Phase 15 (PART-01).

**Still owed:** a proper legal study of the matrix (obligations per licence, one-way rules, and
whether a user contribution needs its own licence slug or a source dimension). Recorded in
`12-CONTEXT.md` § Deferred Ideas; not a phase 12 deliverable.

### Gaps Summary

No code gap blocks the phase. Everything the roadmap asks the system to do is present, wired and
independently re-run during this verification: migration `0011` backfills every existing row from
the reviewed CSV and refuses to finish when a source is unmapped (observed, not merely claimed);
the one answer write path stamps provenance, enforces ownership and freshness across every NULL
combination, and journals the losing value; `contribute` and the AccesLibre importer both inherit
it; the detail endpoint exposes `source` / `license` / `observed_at` on the place and on each
answer while the search list stays byte-identical; the redistribution matrix is reviewed data with
a pure predicate, a SQL twin proven to agree on every pair, and an operator exclusion report; and
the licence catalogue is loaded by the seed and by `admin licences sync` with an exit-1 audit.

Three gaps are **accepted and carry no blocker**:

1. **D-14 exit-point counters** travel with Phase 14 — there is no export or import report to count
   against yet. Phase 12 ships the predicate, the SQL twin and `admin licences excluded`.
2. **`user → odbl` versus the `lov2_partner` destination** is deferred to Phase 15; the reviewed
   matrix currently withholds user contributions from that destination.
3. **`reason='not_redistributable'`** stays reserved in the `place_accessibility_write` check
   constraint with no producer this phase.

The one human item — legal review of the six matrix cells the phase did not specify — was
**accepted by the operator on 2026-11-13** as a provisional posture ("on pourra rechanger plus tard
si besoin, il va falloir étudier ça correctement"). That acceptance is why the status is `passed`
rather than `human_needed`; the deeper legal study is recorded as debt in `12-CONTEXT.md`, not as a
phase gap.

---

_Verified: 2026-11-13T12:38:44Z_
_Verifier: the agent (gsd-verifier)_
