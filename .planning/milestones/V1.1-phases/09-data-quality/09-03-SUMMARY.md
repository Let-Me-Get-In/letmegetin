---
phase: 09-data-quality
plan: 03
subsystem: curation
tags: [duplicates, review-queue, coverage, csv, admin-cli, postgis, data-quality]

requires:
  - phase: 09-data-quality
    provides: 09-02 importer (0.60–0.90 review bucket) and the alias CSV
provides:
  - "migration 0010: place.duplicate_of_id (+ FK/index) and place_review_decision (merge/reject audit)"
  - "duplicates list|merge|reject on the admin CLI, soft merge only (canonical_id + alias + merge log)"
  - "coverage [--format table|csv] [--out PATH]: places, places with values and fill rate per category/country"
affects: [curation, reporting, search-quality]

actuals:
  tokens: 12800
  tasks: 2
  commits: 1
  plan_head_before: 237c8772ba8a3e47a6594b93108b4acb15ff5c68
  plan_head_after: 34b8a86b2bd143f218426ed44c99017c780bbbb1

tech-stack:
  added: []
  patterns:
    - "Review queue as a persisted FK (duplicate_of_id), not a recomputation of scores"
    - "One aggregate query per export: canonical rows excluded so a merge never double-counts"
    - "Operator decisions are append-only audit rows for merges and rejections alike"

key-files:
  created:
    - migrations/versions/0010_duplicate_review.py
    - src/letmegetin/application/places/duplicates.py
    - src/letmegetin/application/places/coverage.py
    - tests/unit/test_duplicates.py
    - tests/integration/test_places_duplicates.py
  modified:
    - src/letmegetin/domain/places/entities.py
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/application/places/import_acceslibre.py
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/infrastructure/persistence/mappers.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/admin.py
    - README.md

key-decisions:
  - "The importer now persists its review candidate on place.duplicate_of_id: the queue is one indexed read, and the 0.90/0.60 scoring stays untouched."
  - "merge reuses the importer's own writes (canonical_id, alias, merge log) with actor='operator', so an operator merge and an importer merge have the same shape."
  - "A rejection needs its own audit row because place_merge_log only covers merges; place_review_decision records actor, score, note and timestamp for both."
  - "Coverage counts DISTINCT place ids with canonical rows excluded, so a merged duplicate is counted once; unresolved categories are named '(unresolved)', never dropped."
  - "Out-of-band scores are listed with an '[out of band]' marker instead of hidden: a stale flag must be visible to the operator."

patterns-established:
  - "A read-only report that must be safe on production: one SELECT, bump=False, no commit path."
  - "An empty-database contract: every new command is a sane no-op (blank list / 'no places yet', exit 0)."

requirements-completed: [DATA-03, DATA-04]

coverage:
  - id: D1
    description: "Every imported 0.60–0.90 match appears in `duplicates list` with its candidate, score and city"
    requirement: DATA-03
    verification:
      - kind: integration
        ref: "tests/integration/test_places_duplicates.py#test_duplicates_list_shows_the_review_row_with_its_score"
        status: pass
      - kind: other
        ref: "manual fixture run: 1108  0.868  Mediatheque Verif Alpha Annexe -> Médiathèque Vérif Alpha  Testville"
        status: pass
    human_judgment: false
  - id: D2
    description: "`duplicates merge` sets canonical_id, keeps the merged name as an alias, writes place_merge_log and place_review_decision, and removes the place from search"
    requirement: DATA-03
    verification:
      - kind: integration
        ref: "tests/integration/test_places_duplicates.py#test_duplicates_merge_links_the_candidate_and_removes_the_place_from_search"
        status: pass
    human_judgment: false
  - id: D3
    description: "`duplicates reject` keeps both places searchable, records the rejection, and the pair leaves the queue for good"
    requirement: DATA-03
    verification:
      - kind: integration
        ref: "tests/integration/test_places_duplicates.py#test_duplicates_reject_keeps_both_places_and_records_the_decision"
        status: pass
    human_judgment: false
  - id: D4
    description: "Both actions refuse a place with no pending candidate (DomainError → exit 1) and nothing is deleted"
    requirement: DATA-03
    verification:
      - kind: unit
        ref: "tests/unit/test_duplicates.py (merge/reject refusal, alias/merge-log/decision counts, band edges)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_places_duplicates.py#test_duplicates_actions_refuse_a_place_without_a_candidate"
        status: pass
    human_judgment: false
  - id: D5
    description: "`coverage --format csv` exports one row per category/country with places, places with values and fill rate, counting merged places once and naming unresolved categories"
    requirement: DATA-04
    verification:
      - kind: integration
        ref: "tests/integration/test_places_duplicates.py#test_coverage_csv_counts_places_by_category_and_country"
        status: pass
      - kind: other
        ref: "manual run on the fixture: library,FR,1,0,0.0 / museum,FR,2,0,0.0 / total,,3,0,0.0"
        status: pass
    human_judgment: false
  - id: D6
    description: "Both commands are no-ops on the current empty database (exit 0)"
    requirement: DATA-04
    verification:
      - kind: integration
        ref: "tests/integration/test_places_duplicates.py#test_commands_are_noops_on_an_empty_place_table"
        status: pass
      - kind: other
        ref: "manual run with 0 places: `duplicates list` blank, `coverage --format csv` header + 'no places yet', both exit 0"
        status: pass
    human_judgment: false
  - id: D7
    description: "The first national load: run the real import, review the queue, merge/reject, export coverage"
    requirement: DATA-03
    verification: []
    human_judgment: true
    rationale: "The Acceslibre export is not in the repo and the load is an operator action on a host; it cannot be exercised from CI."

duration: 55min
completed: 2026-11-05
status: complete
---

# Phase 9 Plan 03: Duplicate review queue and coverage export Summary

**The importer's 0.60–0.90 candidates are now persisted, listable and resolvable from the admin CLI (soft merge or audited rejection), and coverage by category and country exports as CSV — both sane no-ops on the current empty database.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-11-05
- **Tasks:** 2
- **Files changed:** 13 (5 created)
- **Commit:** `34b8a86` — 984 insertions (one plan commit per repo rule)

## Accomplishments

- Migration `0010` adds `place.duplicate_of_id` (FK `SET NULL`, indexed) and `place_review_decision` (place/candidate FKs, score, `decision IN ('merge','reject')`, actor, note, created).
- The importer persists the review candidate (`duplicate_of_id=candidate.id` when `classify_match` returns `review`); the thresholds and the score written to `confidence` are unchanged.
- `application/places/duplicates.py`: `list_pending` (indexed queue, score desc), `merge_duplicate` (canonical link → clear flag → status open → alias when names differ → merge log → decision), `reject_duplicate` (clear flag, keep both rows, decision row), and `in_review_band`.
- `application/places/coverage.py`: `CoverageRow`, `coverage()` (fill rate + totals), `coverage_csv` (stdlib `csv`), `coverage_table`.
- `SqlAlchemyCoverageRepository.by_category_country`: one aggregate query, canonical rows excluded, unresolved categories named.
- CLI: `duplicates list [--limit]`, `duplicates merge PLACE_ID [--note]`, `duplicates reject PLACE_ID [--note]`, `coverage [--format table|csv] [--out PATH]`; reads use `bump=False`, writes use the default bump.
- Tests: 6 unit cases on fakes, 8 integration cases (queue, out-of-band marker, merge incl. search exclusion, reject, refusal, coverage CSV + `--out`, empty DB).
- README documents both commands and what the CSV is for.

## Task Commits

1. **Task 1 + Task 2** — `34b8a86` (feat) — `LET-33 feat(curation): add the duplicate review queue and the coverage export`

## Verification (real output)

```
$ uv run ruff check .                       -> All checks passed!
$ uv run mypy                               -> Success: no issues found in 73 source files
$ uv run bandit -r src -c pyproject.toml    -> Low 0, Medium 0, High 0
$ uv run pytest -q --cov=letmegetin --cov-branch --cov-fail-under=85
233 passed, 1 warning in 34.46s — Total coverage: 92.69% (floor 85%)
```

Migration round-trip on `localhost:55433`:

```
$ uv run alembic downgrade -1   -> Running downgrade 0010 -> 0009
  duplicate_of_id columns=0 ; place_review_decision=None ; alembic current = 0009
$ uv run alembic upgrade head   -> Running upgrade 0009 -> 0010
  duplicate_of_id columns=1 ; place_review_decision=place_review_decision ; 0010 (head)
```

Empty database (0 places, the state dev and prod are in until the national load):

```
$ ... duplicates list
(blank line)                         exit=0
$ ... coverage --format csv
category,country,places,with_accessibility,fill_rate
no places yet                        exit=0
```

On the import fixture (`cli-test-verify-*`, 3 rows → 1 auto-link + 1 review):

```
$ ... import acceslibre --file a.csv
acceslibre import: created=3 linked=1 review=1 skipped=0 resolved=3 unresolved=0 dry_run=False

$ ... duplicates list
1108	0.868	Mediatheque Verif Alpha Annexe -> Médiathèque Vérif Alpha	Testville

$ ... duplicates merge 1108 --note "même médiathèque"
duplicate merged: 1108 -> 1106

$ ... duplicates list                 -> (blank) exit=0
$ list_near(45.1, 5.1, 500)           -> ['Médiathèque Vérif Alpha']   # merged place gone
rows: (verify-1,None,None,open) (verify-2,1106,None,open) (verify-3,1106,None,open)
place_merge_log: (1106, 1108, 0.868, 'operator')
place_review_decision: ('merge', 'operator', 1106, 'même médiathèque')
place_alias(1106): Mediatheque Verif Alpha, Mediatheque Verif Alpha Annexe
```

Rejection on a second pair:

```
$ ... duplicates list
1110	0.846	Musee Verif Bis -> Musée Vérif	Testville
$ ... duplicates reject 1110 --note "annexe distincte"
duplicate rejected: 1110 (both places kept)
$ ... duplicates list                 -> (blank) exit=0
place_review_decision: ('reject', 'operator', 1109, 'annexe distincte')
list_near(45.4, 5.4, 500)             -> ['Musee Verif Bis', 'Musée Vérif']  # both kept
```

Coverage on those rows (merged `1108` excluded, rejected `1110` counted):

```
$ ... coverage --format csv
category,country,places,with_accessibility,fill_rate
library,FR,1,0,0.0
museum,FR,2,0,0.0
total,,3,0,0.0
```

The fixture rows were deleted afterwards (`remaining places: 0`); no real row was touched.

## Decisions Made

- `duplicate_of_id` is written by `SqlAlchemyPlaceRepository.add`/`update` (the plan-carried correction), so the importer and any future writer persist it in one place.
- The merge path writes the alias only when the names differ case-insensitively, mirroring the importer.
- `coverage` is read-only end to end: one SELECT, `bump=False`, no commit, aggregated integers only.
- Empty coverage output keeps the header then `no places yet` so the no-data state is explicit and still exit 0.

## Deviations from Plan

1. **[Interface] `merge_duplicate`/`reject_duplicate` take no separate `decisions` argument.** `add_review_decision` lives on `PlaceRepository` (as the plan's artifacts list says), so passing a second repository object would have meant passing the same instance twice. Unit tests still isolate the decision log through the fake.
2. **[Interface] `coverage()` takes only the coverage repository.** The draft signature carried an unused `places` argument; the export never touches the place port directly.
3. **[Interface] `SqlAlchemyCoverageRepository.by_category_country()` returns tuples, not `CoverageRow`.** Matches the existing `count_by_source` / `unresolved_categories` style; `CoverageRow` stays in `application/places/coverage.py` as the plan specifies.
4. **[Test] Reject test asserts the rejected name is not aliased, not "no aliases".** The fixture's auto-link already writes an alias on the candidate; asserting an empty alias table would test the importer, not the rejection.
5. **[Formatting] `ruff format` reflowed `models.py` and the integration test** on the first commit attempt; re-staged, no behavioural change.
6. **[Process] Committed on `main`, like waves 1–2.** `branching_strategy` is `none` and the phase work already lives on `main`; no branch was created.

**Total deviations:** 6 (3 interface drafts, 1 test assertion, 1 formatting, 1 process).
**Impact on plan:** none on scope or acceptance; all seven must-have truths hold and are tested.

## Issues Encountered

- The first coverage `--out` assertion expected `len(rows)` data rows while the CLI reports data rows excluding the totals row; corrected the assertion to the actual contract (4).
- `psql` is not installed on this workstation; database checks used the async SQLAlchemy session instead.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. No HTTP endpoint, no secret, no new dependency (stdlib `csv` + SQLAlchemy aggregates). Merge is soft (`canonical_id`, alias, merge log, decision); rejection keeps both rows; coverage exports aggregated counts only.

## Next Phase Readiness

- DATA-03 and DATA-04 are implemented and verified on the fixture and on an empty database.
- Remaining human steps for phase close:
  1. Run the national Acceslibre load: download the export, `--dry-run`, complete the 131 alias gaps, import, `import report` → 0.
  2. Work the queue: `duplicates list`, merge/reject the real candidates, then `coverage --format csv --out …` for the first reporting extract.
  3. Run `families sync` + `families audit` (DATA-01) and the import report (DATA-02) on the dev and prod hosts after deploy.
- No planning file was committed: `STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md` and the three phase summaries stay uncommitted for the phase-close docs commit.

## Self-Check: PASSED

- `migrations/versions/0010_duplicate_review.py` — FOUND
- `src/letmegetin/application/places/duplicates.py` — FOUND
- `src/letmegetin/application/places/coverage.py` — FOUND
- `tests/unit/test_duplicates.py` — FOUND
- `tests/integration/test_places_duplicates.py` — FOUND
- commit `34b8a86` — FOUND (ancestor of HEAD)
- `0010` applies, downgrades and re-applies — VERIFIED

---
*Phase: 09-data-quality*
*Completed: 2026-11-05*
