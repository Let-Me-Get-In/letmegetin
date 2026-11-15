---
phase: 15-acceslibre-round-trip
plan: 04
subsystem: export
tags: [lov2-partner, projection, identifier-rule, mapping-document, acceslibre, export-header, erp_slug]

# Dependency graph
requires:
  - phase: 14-open-odbl-export
    provides: the snapshot export, its seven CSV entries and the licence-gated streams
  - phase: 15-acceslibre-round-trip
    provides: export_odbl(destination=…), resolve_identifier and place.erp_slug (15-01..15-03)
provides:
  - the pure projection our keys -> AccesLibre's identifier / activite / field names
  - THEIR_FIELD_FOR_SLUG, the 8-entry inverse of FIELD_MAP
  - build_lov2_feed, Lov2ExportRepository and the parameterised _write_zip(headers=…)
  - data/referential/acceslibre_mapping.csv + its fail-closed loader
  - the importer's slug column, so a re-import fills place.erp_slug
affects: [15-05-push-use-case, 15-06-journal, 16-osm-export]

actuals:
  tokens: 26446
  tasks: 2
  commits: 2
  plan_head_before: a05a1bdf2d4edc588997cc7a84db6f6ffc43dd3b
  plan_head_after: 9d0b98414f495443f80098e669035e09514c9896

tech-stack:
  added: []
  patterns:
    - "the vocabulary transform lives in a pure projection; the writer only ever sees to_csv() rows"
    - "a decorator over the export repository is the one seam between our rows and the partner feed"
    - "unmappable rows are accumulated and deduplicated by (entity, identifier, reason), so a blocked rule writes one row, not 635k"

key-files:
  created:
    - src/letmegetin/domain/places/lov2_projection.py
    - src/letmegetin/application/places/lov2_export.py
    - data/referential/acceslibre_mapping.csv
    - tests/unit/domain/places/test_lov2_projection.py
  modified:
    - src/letmegetin/domain/places/acceslibre_map.py
    - src/letmegetin/domain/places/export_plan.py
    - src/letmegetin/domain/places/entities.py
    - src/letmegetin/application/places/export.py
    - src/letmegetin/application/places/import_acceslibre.py
    - src/letmegetin/infrastructure/persistence/export_repositories.py
    - src/letmegetin/infrastructure/persistence/mappers.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/admin.py
    - docs/public-api.md
    - tests/functional/places/test_lov2_export.py

key-decisions:
  - "Every diverted row is deduplicated by (entity, identifier, reason) with a count, so the `blocked` default writes one `place;;identifier_unresolved` row instead of one per place."
  - "The mapping sidecar merges the reviewed document with the run's diversions; a reviewed detail wins over an empty diverted one, and no entry is duplicated."
  - "The mapping document is a reviewed referential artifact (232 criteria = criteria.json + the base grid minus the 8, plus 133 canonical activite rows), so it is a superset of any seeded DB; the coverage test asserts DB ⊆ document."
  - "The `slug` column alias is always read by the importer rather than gated on the recorded rule: a missing column yields None and writes nothing, so gating would add coupling for no safety."
  - "`refuse_partner_window` was extracted so the CLI dispatch and export_odbl share the one 'partner feeds are full snapshots only' guard (a 15-01 behaviour)."

patterns-established:
  - "Partner feed = the Phase 14 writer + an ExportHeaders set + a projecting repository decorator; no second serialiser."
  - "The reviewed mapping document is data with a loader that fails closed on a duplicate, empty or mis-headered row."

requirements-completed: [PART-01]

coverage:
  - id: D1
    description: "The pure projection keys a place on resolve_identifier (slug-first, origin_id fallback, blocked -> unmappable), a category on its max-places activite, an answer on one of the 8 field names"
    requirement: PART-01
    verification:
      - kind: unit
        ref: "tests/unit/domain/places/test_lov2_projection.py (27 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "`admin export odbl --destination lov2_partner` emits partner keys in all seven entries, no slug/category_slug/criterion_slug column, and diverts unmappable rows to mapping.csv"
    requirement: PART-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_lov2_export.py#test_cli_emits_partner_keys_in_every_entry"
        status: pass
      - kind: functional
        ref: "tests/functional/places/test_lov2_export.py#test_mapping_document_names_every_unmappable_place"
        status: pass
      - kind: functional
        ref: "tests/functional/places/test_lov2_export.py#test_blocked_rule_diverts_every_place"
        status: pass
    human_judgment: false
  - id: D3
    description: "The mapping document names every DB criterion outside FIELD_MAP (the coverage test fails on a gap) and the loader fails closed on a truncated or duplicate row"
    requirement: PART-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_lov2_export.py#test_every_db_criterion_is_in_the_mapping_document"
        status: pass
      - kind: functional
        ref: "tests/functional/places/test_lov2_export.py#test_the_mapping_loader_fails_closed"
        status: pass
    human_judgment: false
  - id: D4
    description: "A re-import fills place.erp_slug from AccesLibre's slug column and never overwrites a user-owned answer"
    requirement: PART-02
    verification:
      - kind: functional
        ref: "tests/functional/places/test_lov2_export.py#test_reimport_preserves_owned_answers_and_fills_the_erp_slug"
        status: pass
    human_judgment: false
  - id: D5
    description: "The partner identifier rule stays `blocked;UNVERIFIED` until LET-130, so the production feed is header-only and every row diverts by design"
    human_judgment: true
    rationale: "The live probe needs the AccesLibre key that does not exist yet (15-03 task 2, blocking-human). The mechanism is proven against a pinned rule; the production outcome flips when the key lands."

duration: 38min
completed: 2026-11-15
status: complete
---

# Phase 15 Plan 04: lov2 partner feed and mapping document Summary

**The Phase 14 export now speaks AccesLibre's vocabulary: places keyed on `resolve_identifier` with the canonical `activite`, answers keyed on the 8 field names, and every row it cannot express lands in a `mapping.csv` sidecar with a reason instead of vanishing.**

## Performance

- **Duration:** ~38 min
- **Started:** 2026-11-15T19:08:00Z
- **Completed:** 2026-11-15T19:46:00Z
- **Tasks:** 2
- **Files modified:** 15 (3 created)

## Accomplishments

- `THEIR_FIELD_FOR_SLUG` is the 8-entry inverse of `FIELD_MAP`, asserted bijective at import.
- `domain/places/lov2_projection.py` (pure): `canonical_activites` picks the largest-population `activite` per category; `project_place` keys on `resolve_identifier` and diverts a `blocked` rule, a `slug` rule without `erp_slug`, a missing `origin_id` or a category with no inverse; `project_answer` emits `value["value"]` only — never `user_id`; `project_category`/`project_criterion`/`project_alias` complete the vocabulary.
- `_write_zip`/`export_odbl` take an `ExportHeaders` set; `OPEN_EXPORT_HEADERS` keeps the ODbL call site byte-identical (the full places suite still green).
- `build_lov2_feed` wraps the repository in `Lov2ExportRepository`, so ATTRIBUTION and the manifest are built from the same projected rows that reach the archive, then writes `mapping.csv` next to `latest.json` — never inside the ZIP.
- `data/referential/acceslibre_mapping.csv`: 366 rows — the D-05 deviation note, 232 criteria outside `FIELD_MAP` (the 8 excluded), 133 canonical `activite` choices. `load_acceslibre_mapping` fails closed on a duplicate, an empty field or a mis-headered file.
- The importer reads AccesLibre's `slug` column and carries it on `Place`/`PlaceModel`, so a re-import fills `place.erp_slug` while `upsert_accessibility` keeps a user-owned answer (`source='user'`) intact.
- `docs/public-api.md` gains the "lov2 partner feed" section: partner keys, the sidecar, and the header-only outcome while the rule is `blocked`.

## Task Commits

1. **Task 1: The pure projection — slug-first identifier, canonical category inverse, field inverse** — `8f3345a` (feat)
2. **Task 2: Wire the projection, populate erp_slug, and emit the reviewed mapping document** — `9d0b984` (feat)

**Plan metadata:** the close-out commit carrying this SUMMARY.

## Verification (real output)

| Check | Command | Result |
|---|---|---|
| Unit projection | `uv run pytest tests/unit/domain/places/test_lov2_projection.py -m unit -x` | 27 passed |
| Functional feed | `uv run pytest tests/functional/places/test_lov2_export.py -m functional -x` | 9 passed |
| Lint | `uv run ruff check src tests` / `--format --check` | All checks passed / 162 files already formatted |
| Types | `uv run mypy` | Success: no issues found in 92 source files |
| Security | `uv run bandit -r src -c pyproject.toml` | no findings |
| Full suite | `uv run pytest -q` | 579 passed in 143.92s |
| Places suite | `uv run pytest tests/functional/places -m functional` | 102 passed |

## Files Created/Modified

- `src/letmegetin/domain/places/acceslibre_map.py` — `THEIR_FIELD_FOR_SLUG` + bijection assert.
- `src/letmegetin/domain/places/lov2_projection.py` — the pure projection, its LOV2 headers, projected/unmappable rows and `MappingRow`.
- `src/letmegetin/domain/places/export_plan.py` — `CsvRow`, `SourcedRow` (read-only properties, so frozen rows satisfy it), `ExportHeaders` + `OPEN_EXPORT_HEADERS`; `PlaceRow.erp_slug`; `AliasRow` identifier candidates.
- `src/letmegetin/application/places/export.py` — `headers` threaded through `_write_zip`/`export_odbl`, `_seeing` widened to `SourcedRow`, `refuse_partner_window` extracted.
- `src/letmegetin/application/places/lov2_export.py` — `build_lov2_feed`, `Lov2ExportRepository`, `load_identifier_rule`, `load_canonical_activites`, `load_acceslibre_mapping`, `merge_mapping`.
- `src/letmegetin/application/places/import_acceslibre.py` — `slug` column alias, `AcceslibreRow.erp_slug`, existing-row refresh.
- `src/letmegetin/domain/places/entities.py`, `infrastructure/persistence/{mappers,repositories}.py` — `Place.erp_slug` through the write path (fill-only).
- `src/letmegetin/infrastructure/persistence/export_repositories.py` — `PlaceModel.erp_slug` streamed; `stream_aliases` joins the canonical place for both sides' candidates.
- `src/letmegetin/admin.py` — `lov2_partner` dispatches to `build_lov2_feed`, prints the sidecar path, shares the snapshot-only guard.
- `data/referential/acceslibre_mapping.csv` — the reviewed mapping document.
- `docs/public-api.md` — the "lov2 partner feed" section.
- `tests/unit/domain/places/test_lov2_projection.py`, `tests/functional/places/test_lov2_export.py`.

## Decisions Made

- **Diverted rows are counted, not listed.** A `blocked` rule diverts 634 931 places; the accumulator keys on `(entity, identifier, reason)` and writes one row with a count, so the sidecar stays bounded and readable.
- **Reviewed detail wins.** When a diverted criterion collides with a reviewed row, the reviewed `detail` is kept; a new criterion (absent from the document) is appended, which is D-08's "never silently omit" holding at export time too.
- **The mapping document is generated from the reviewed referential, not from a live DB**, so it is reviewable in a diff and a superset of any seeded environment; the coverage test proves DB ⊆ document.
- **`SourcedRow` uses read-only properties**, because a `frozen=True, slots=True` dataclass cannot satisfy a settable protocol attribute.
- **One guard for partner windows.** `refuse_partner_window` is called by `export_odbl` and by the CLI, so `--delta` with `lov2_partner` still fails with the 15-01 message instead of silently producing a snapshot.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `PlaceRow.erp_slug` and `AliasRow` identifier candidates landed in Task 1**
- **Found during:** Task 1
- **Issue:** `project_place` reads `row.erp_slug` and `project_alias` needs both sides' candidates; the plan schedules both dataclass changes for Task 2, so Task 1 could not compile.
- **Fix:** added the defaulted `erp_slug` field and the four candidate fields (default `None`, never serialised) to `export_plan.py` in Task 1; Task 2 populated them from SQL.
- **Files modified:** `src/letmegetin/domain/places/export_plan.py`
- **Commit:** `8f3345a`

**2. [Rule 3 - Blocking] `ProjectedCategory`, `ProjectedCriterion` and `MappingRow` added to the projection module**
- **Found during:** Task 2
- **Issue:** the plan lists only place/answer dataclasses, but `_write_csv_entry` needs a `to_csv()` row for categories and criteria, and the sidecar needs a row type shared by the reviewed document and the run's diversions.
- **Fix:** added the three frozen dataclasses plus `project_category`/`project_criterion`, keeping the vocabulary transform in the pure module.
- **Commit:** `9d0b984`

**3. [Rule 3 - Blocking] The erp_slug write path needed four files outside `files_modified`**
- **Found during:** Task 2
- **Issue:** `place.erp_slug` existed only as a column; the entity, mapper and repository never carried it, so the importer could not fill it.
- **Fix:** `Place.erp_slug`, `place_from_model`, `repository.add`/`update` (fill-only, so an export without a slug column never clears it).
- **Files modified:** `domain/places/entities.py`, `infrastructure/persistence/mappers.py`, `infrastructure/persistence/repositories.py`
- **Commit:** `9d0b984`

**4. [Rule 1 - Bug] The CLI bypassed the "partner feeds are full snapshots only" guard**
- **Found during:** Task 2
- **Issue:** routing `lov2_partner` straight to `build_lov2_feed` skipped the guard inside `export_odbl`, so `--delta` would have produced a snapshot instead of the 15-01 `DomainError`.
- **Fix:** extracted `refuse_partner_window` in `export.py`, called it from both `export_odbl` and the CLI callback, and added `test_partner_feed_refuses_a_delta`.
- **Commit:** `9d0b984`

**5. [Rule 1 - Bug] The two 15-01 feed tests had to pin the rule**
- **Found during:** Task 2
- **Issue:** with the committed `blocked;UNVERIFIED` rule, the projection correctly empties `places.csv`, which invalidated the licence-gate assertion.
- **Fix:** a `partner_data` fixture patches `settings.data_dir` to a tmp referential (rule `origin_id;VERIFIED`, the four committed CSVs); both existing tests use it, which is exactly the plan's named seam.
- **Commit:** `9d0b984`

### Deviations (recorded, not defects)

**6. [Deviation - Condition] `erp_slug` population is unconditional**
- **Found during:** Task 2
- **Issue:** the plan says "populate when the recorded rule is `slug`; when `origin_id`/`blocked`, skip".
- **Fix:** the `slug` column alias is always read — a missing column yields `None` and writes nothing, so gating on the rule would couple the importer to the rule file with no safety gain.
- **Impact:** none on the feed; `resolve_identifier` still ignores `erp_slug` when the rule is not `slug`.

**7. [Deviation - Data] The mapping document is a superset of the DB criteria**
- **Found during:** Task 2
- **Issue:** a DB's criteria set is environment-dependent (61 seeded locally, 240 in the reviewed referential).
- **Fix:** generated from `criteria.json` ∪ `category_grids/category-1.json` minus the 8 = 232 rows; the coverage test asserts the DB set is a subset, and skips test-fixture criteria.

## Issues Encountered

- The GitNexus index remains stale (last indexed `64d2b27`); `impact` was not trusted for `export.py`/`repositories.py` edits. The full suite (579 tests) and mypy over 92 files are the evidence instead.
- The mapping CSV is written with `;` (the reviewed convention) and read with `csv.DictReader(delimiter=';')`; the first run used the csv default and the loader caught it — the fail-closed header check did its job.

## User Setup Required

None. No dependency was added and no secret was read. The partner key (`LETMEGETIN_ACCESLIBRE_API_KEY`, LET-130) stays the only outstanding external input, and it is not needed by this plan.

## Next Phase Readiness

- **15-05 (push)** can read `place.erp_slug` (importer-filled, mapper-carried) and keep using `resolve_identifier` as the single key rule; `OwnedAnswer.erp_slug` is now populated on the write path.
- **The rule is still `blocked;UNVERIFIED`.** In production the feed is header-only and every place diverts to `mapping.csv` — the designed fail-closed behaviour until the probe runs (D-05, T-15-06). Nothing in this plan keys on an unverified `origin_id`.
- **The sidecar contract** is `entity;identifier;reason;detail`, merged reviewed + diverted, and `load_acceslibre_mapping` fails closed — a later API route or a hand delivery can reuse it unchanged.
- **`Lov2ExportRepository` is a decorator, not a protocol conformance**; `build_lov2_feed` casts it because the writer only needs `to_csv()` and the provenance fields. A future second destination should reuse `ExportHeaders`, not the cast.

---

## Self-Check: PASSED

- `src/letmegetin/domain/places/lov2_projection.py` — FOUND, 27 unit tests green.
- `src/letmegetin/application/places/lov2_export.py` — FOUND, 9 functional tests green.
- `data/referential/acceslibre_mapping.csv` — FOUND, 366 rows, loader round-trips it.
- Commits `8f3345a` and `9d0b984` — both ancestors of HEAD.
- Full suite: 579 passed; ruff, ruff format, mypy and bandit clean.

*Phase: 15-acceslibre-round-trip*
*Completed: 2026-11-15*
