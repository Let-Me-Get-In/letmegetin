---
phase: 16-openstreetmap
plan: 03
subsystem: places
tags: [osm, dedup, importer, merge-log, alias, review-queue, report, postgis]

requires:
  - phase: 16-openstreetmap (16-01)
    provides: OsmRow, iter_osm_rows, import osm, OsmImportReport.unmatched, render_unmatched
  - phase: 16-openstreetmap (16-02)
    provides: reviewed category_mapping.osm_tag, osm_accessibility_tags.csv, source_licences osm;odbl
  - phase: 03-dedup
    provides: get_candidates (100 m block), similar_score, classify_match, place_alias, place_merge_log
provides:
  - import_osm._candidate — the phase-3 scorer run against our own database, never an external API
  - OSM duplicate wiring — auto match becomes a linked row (canonical_id + alias + merge log)
  - OSM review diversion — a 0.75-0.90 match gets duplicate_of_id + operating_status=duplicate_review
  - `import osm --no-dedup` / `--dry-run` honoured on the dedup path
  - unmatched tag combinations rendered per distinct set, most frequent first
affects: [16-04 .osmChange generator, 17-overture]

actuals:
  tokens: 4754
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Source-agnostic dedup, third importer: one scorer, one 100 m block, reviewed thresholds, no per-source branch (D-07)"
    - "A duplicate is a soft link plus an audit row — nothing is deleted or hard-merged (D-08)"

key-files:
  created:
    - tests/unit/application/places/test_import_osm.py
  modified:
    - src/letmegetin/application/places/import_osm.py
    - tests/functional/places/test_osm_import.py

key-decisions:
  - "_candidate mirrors import_acceslibre._candidate verbatim: get_candidates blocks at DEFAULT_CANDIDATE_RADIUS, similar_score scores, max() picks the best — the scorer is reused, not re-derived"
  - "The unmatched report joins a combination with '|' so a tag value's own spaces no longer blur where one combination ends and the next begins"
  - "The functional duplicate target is created through SqlAlchemyPlaceRepository.add, not raw SQL: the test exercises the same licence-snapshotting write path the import will meet"
  - "The review bucket gets its own functional case: duplicate_of_id is a column write, which an in-memory fake cannot prove"

patterns-established:
  - "Duplicate proof is asserted on all three artefacts at once: canonical_id on the row, place_alias for the kept name, place_merge_log for the audit"

requirements-completed: [OSM-01]

coverage:
  - id: D1
    description: "An OSM POI whose nearest neighbour scores >= 0.90 is linked: canonical_id set, name kept as an alias, merge logged with actor='osm'; a 0.75-0.90 match is diverted to review (duplicate_of_id, duplicate_review); below 0.75 stays new"
    requirement: OSM-01
    verification:
      - kind: unit
        ref: "tests/unit/application/places/test_import_osm.py (14 tests: category resolution, classify_match boundaries, report ranking, link/review/no-dedup wiring)"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_osm_import.py::test_osm_import_links_a_duplicate_of_another_source_place"
        status: pass
    human_judgment: false
  - id: D2
    description: "`import osm --no-dedup` skips the candidate lookup and imports the POI unlinked; `--dry-run` writes no place, alias or merge row"
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_import.py::test_osm_import_no_dedup_creates_an_unlinked_place, ::test_osm_import_dry_run_writes_nothing"
        status: pass
    human_judgment: false
  - id: D3
    description: "The report names each unmatched tag combination (key=value|key=value), most frequent first, and never guesses a category from it"
    verification:
      - kind: unit
        ref: "tests/unit/application/places/test_import_osm.py::test_render_unmatched_ranks_by_count_then_tag"
        status: pass
      - kind: integration
        ref: "tests/functional/places/test_osm_import.py::test_osm_import_writes_one_place_with_version_and_raw_tags"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-11-16
status: complete
---

# Phase 16 Plan 03: OpenStreetMap dedup and unmatched report Summary

**An OSM POI that already exists as an AccesLibre place imports as a linked row — canonical_id, alias, merge log — never a duplicate; a 0.75–0.90 near miss goes to the review queue, and the report names each unmapped tag combination most frequent first**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)
- **Commits:** 2

## Accomplishments

- **The Phase-3 scorer now runs inside the OSM import, unchanged.** `_candidate` asks
  `places.get_candidates(lat, lng, name)` (the `DEFAULT_CANDIDATE_RADIUS = 100.0` spatial block),
  scores each neighbour with `similar_score`, and keeps the best — no external API, no OSM-specific
  dedup rule (D-07).
- **A duplicate is a link, not a second place.** `classify_match` decides: ≥ 0.90 sets `canonical_id`,
  writes `place_merge_log` (`actor='osm'`) and keeps the weaker name in `place_alias`; 0.75–0.90 sets
  `duplicate_of_id` + `operating_status='duplicate_review'`; below 0.75 stays a new place. Nothing is
  deleted or hard-merged (D-08).
- **`--no-dedup` and `--dry-run` are honoured on the new path.** `--no-dedup` skips the per-row
  PostGIS lookup for the initial national load (same documented fast path as AccesLibre);
  `--dry-run` returns after counting, before `places.add`, so no place, alias or merge row exists.
- **The unmatched report reads per combination.** `key=value|key=value = count`, most frequent first
  then by tag string — the operator sees exactly which OSM tags `category_mapping` is missing (D-06).
- **Proven at two levels**: 14 unit tests over the pure seam (category resolution, the threshold
  boundaries, the report ranking, and the link/review/no-dedup wiring through fake ports) and 13
  functional tests through the real CLI and PostGIS.

## Task Commits

1. **Task 1: link duplicates through the phase-3 scorer** — `fe4f62c` (feat)
2. **Task 2: name unmatched tag combinations, prove dedup** — `e1aedad` (feat)

## Files Created/Modified

- `src/letmegetin/application/places/import_osm.py` — `_candidate`, the `_import_row` dedup path
  (`canonical_id` / `duplicate_of_id` / `confidence` / `operating_status`), `report.linked` and
  `report.review`, the merge-log + alias write, the `|`-joined `render_unmatched`, and a module
  docstring that no longer calls `dedup` inert.
- `tests/unit/application/places/test_import_osm.py` — pure-seam tests plus in-memory `FakePlaces`,
  `FakeMapping`, `FakeAliases`, `FakeMerges`; an empty reviewed accessibility CSV points the loader
  at `tmp_path`.
- `tests/functional/places/test_osm_import.py` — `_acceslibre_place` (created through the real
  repository), the link / review / `--no-dedup` cases, and a `_CLEANUP` that also removes the
  `test-osm-%` AccesLibre targets (their alias and merge rows cascade).

## Decisions Made

- **The functional duplicate target goes through `SqlAlchemyPlaceRepository.add`, not raw SQL.** It
  is the same write path the import meets, so the licence snapshot and `name_normalized` are real;
  raw SQL would have had to re-derive both.
- **The review bucket has a functional case as well as a unit one.** `duplicate_of_id` is a column
  write; the in-memory fake proves the field is set on the entity, only PostGIS proves it lands.
- **The `|` separator follows the plan.** A combination carries `name=Café du Coin`, whose spaces
  made the old space-joined output ambiguous; `|` marks the boundary between tag pairs.
- **`dedup=False` skips `_candidate` entirely** rather than scoring and ignoring the score — the
  point of the flag is to avoid the per-row proximity query.

## Deviations from Plan

### Auto-fixed Issues

None. Both tasks ran as written, with one plan-explicit detail confirmed rather than changed (the
`|` separator) and one scope note below.

### Scope notes

**1. The unit file imports more than `import_osm.py` + `dedup.py`**
- **Found during:** Task 1
- **Plan said:** "Import import_osm.py + dedup.py only."
- **Actual:** the fakes need `Place`, `PlaceHit` (entities) and `OsmRow` (osm_map) to build
  candidates and rows, plus the reviewed-CSV header for the empty mapping. These are pure data
  types, so the intent of the constraint — no database, no osmium, no clock — holds.
- **Rule:** not a defect; recorded so the next reader does not read it as scope creep.

## Issues Encountered

- **The GitNexus index was stale** (`lastCommit ebaf722` vs `HEAD c96d5be` before this plan), so
  `impact('import_osm')` answered `UNKNOWN` and `detect_changes` reported `changed_count: 0` with
  `changed_files: 3`. Per the repo rule that a zero means "unseen, not unaffected", callers were
  confirmed by search instead: `import_osm` has exactly one caller (`admin.import_osm_command`) and
  `_import_row` exactly one (`import_osm`), both in the files this plan owns. A reindex is due before
  the next plan that edits a shared symbol.
- **`tests/unit/.../test_import_osm.py` had to be created before the wiring existed** — the first run
  was the RED step: 12 passed (pure seams from 16-01) and the two wiring cases failed on
  `canonical_id is None` / `duplicate_of_id is None`, which is the evidence that the new assertions
  actually test the new code.
- The plan's `<verify>` blocks name `uv run pytest …` unqualified; every database-backed run used
  `LETMEGETIN_DATABASE_URL=…/letmegetin_test`, as the execution rules require (the dev database is
  never migrated by a test run).

## Verification

| Command | Result |
|---|---|
| `uv run pytest tests/unit/application/places/test_import_osm.py -m unit` (before wiring) | `2 failed, 12 passed` — the RED step |
| `uv run pytest tests/unit/application/places/test_import_osm.py -m unit` (after wiring) | `14 passed` |
| `…/letmegetin_test uv run pytest tests/functional/places/test_osm_import.py -m functional` | `13 passed` |
| `uv run ruff check src/letmegetin tests` | `All checks passed!` |
| `uv run ruff format --check .` | `196 files already formatted` |
| `uv run mypy` | `Success: no issues found in 98 source files` |
| `…/letmegetin_test uv run pytest -q` (whole suite, regression sweep) | `644 passed` in 186s |

## Known Stubs

None. `import_osm` now uses every argument of its contract; nothing is inert.

## Threat Flags

None new. T-16-05 (a wrong link canonicalising the wrong place) is mitigated as planned and proved
by the link test; the link is soft and reversible. T-16-06 (the unmatched report) stays an operator
stdout surface carrying no user data.

## Next Phase Readiness

- **16-04 (`.osmChange` generator) is unaffected in shape**: `node/1` is still the single `<modify>`
  candidate with its version and raw tags, and the fixture's documented three-object contract holds.
  Note that a real import now links instead of duplicating, so a linked OSM row carries
  `canonical_id` — the generator should emit for the OSM row itself (`source='osm'`) and let the
  canonical link travel with the export projection, not suppress the row.
- **The operator's first national load should pass `--no-dedup`**, then run the duplicate pass: the
  per-row proximity query is the dominant cost of a 600k-row load (measured on AccesLibre).
- **The unmatched report is the growth mechanism for `category_mapping.osm_tag`** (124/158 reviewed):
  the top lines name the exact `key=value` pairs to review next.
- **A reindex of GitNexus is due** before the next plan touching a shared symbol.

---

*Phase: 16-openstreetmap*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk; both task commits (`fe4f62c`, `e1aedad`) are ancestors of HEAD.
