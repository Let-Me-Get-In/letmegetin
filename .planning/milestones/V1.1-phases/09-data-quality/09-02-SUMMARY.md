---
phase: 09-data-quality
plan: 02
subsystem: import
tags: [acceslibre, category-resolution, csv, streaming, admin-cli, data-quality]

requires:
  - phase: 03-referential-api
    provides: categories, category_mapping and the category grid
  - phase: 09-data-quality
    provides: 09-01 clamp on the seeds and the reviewed-CSV + audit-gate convention
provides:
  - "data/referential/acceslibre_categories.csv consumed as the single alias source (391 labels, 260 mapped, 131 reviewed gaps)"
  - "application/places/category_resolution.py: load_category_aliases + resolve_category (alias → exact slug → category_mapping)"
  - "place.source_category persisted on every import; migration 0009 adds it with an index"
  - "import acceslibre --dry-run/--aliases (streams the CSV) and import report (DATA-02 gate, exit 1 while unresolved)"
affects: [09-03, curation, coverage]

actuals:
  tokens: 8509
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Streaming importer: a generator over the file handle, with the list wrapper kept only for tests"
    - "Resolution order is data-driven and deterministic: alias CSV → exact category slug → ordered mapping lookup"
    - "Raw third-party vocabulary persisted next to the resolved FK, so unresolved data stays queryable"

key-files:
  created:
    - migrations/versions/0009_place_source_category.py
    - src/letmegetin/application/places/category_resolution.py
    - tests/unit/test_category_resolution.py
  modified:
    - src/letmegetin/application/places/import_acceslibre.py
    - src/letmegetin/application/places/__init__.py
    - src/letmegetin/admin.py
    - src/letmegetin/domain/places/entities.py
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/infrastructure/persistence/mappers.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - tests/integration/test_places_import.py
    - README.md
    - docs/deploy.md

key-decisions:
  - "The committed alias CSV is read as-is: keys are slugified real `activite` labels, and its 131 empty rows are deliberate gaps, not loader errors."
  - "Exact category slug is checked before `category_mapping`, and the mapping lookup is ordered by category id, so `restaurant` never lands on `fast_food_restaurant` at random."
  - "`place.source_category` is written on every imported row, even when resolution succeeds, so `import report` is one indexed GROUP BY instead of a run log."
  - "The CLI passes the row iterator to the importer; `load_acceslibre_file` survives only as a test helper."
  - "No HTTP route: curation stays CLI-only and the OpenAPI snapshot is untouched."

patterns-established:
  - "A resolution report that counts source values, not just rows (`unresolved: <value>=<count>`), so the operator edits the alias file directly from the output."
  - "A read-only CLI gate (`import report`) that exits 1 with the actionable list, matching `families audit`."

requirements-completed: [DATA-02]

coverage:
  - id: D1
    description: "A `Bibliothèque médiathèque` row lands on `library`, `Musée` on `museum`, and the raw value is persisted on both"
    requirement: DATA-02
    verification:
      - kind: integration
        ref: "tests/integration/test_places_import.py#test_imported_categories_resolve_and_the_raw_value_is_kept"
        status: pass
    human_judgment: false
  - id: D2
    description: "An unknown activity is counted and persisted instead of silently dropped, and `import report` exits 1 naming it"
    requirement: DATA-02
    verification:
      - kind: integration
        ref: "tests/integration/test_places_import.py#test_import_report_fails_while_a_category_is_unresolved"
        status: pass
    human_judgment: false
  - id: D3
    description: "`--dry-run` reports resolved/unresolved per source value and writes nothing"
    requirement: DATA-02
    verification:
      - kind: integration
        ref: "tests/integration/test_places_import.py#test_dry_run_reports_resolution_and_writes_nothing"
        status: pass
      - kind: other
        ref: "391-row fixture dry run: resolved=260 unresolved=131, place count unchanged at 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "Resolution is immutable in git and deterministic: alias → exact slug → ordered mapping"
    requirement: DATA-02
    verification:
      - kind: unit
        ref: "tests/unit/test_category_resolution.py (8 cases, including the committed CSV and the ambiguous `restaurant` bucket)"
        status: pass
    human_judgment: false
  - id: D5
    description: "First national load: download the export, dry-run, complete the alias CSV, import, `import report` → 0"
    requirement: DATA-02
    verification: []
    human_judgment: true
    rationale: "The export is not in the repo and the load is an operator action on a host (licence + hundreds of MB)."

duration: 35min
completed: 2026-11-05
status: complete
---

# Phase 9 Plan 02: Acceslibre category resolution Summary

**Every imported Acceslibre activity now resolves through one reviewed 391-label CSV, in a deterministic order, with the raw value kept on `place.source_category` and a CLI gate that refuses to call the import done while anything is unresolved.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-11-05
- **Tasks:** 2
- **Files modified:** 14 (3 created)
- **Commit:** 1 plan commit (+498/−45 lines)

## Accomplishments

- `data/referential/acceslibre_categories.csv` is now consumed (not regenerated): its 391 real `activite` labels give 260 resolved aliases and 131 deliberate gaps.
- `application/places/category_resolution.py` loads the aliases once (duplicate slug → `DomainError`, empty target = reviewed gap) and resolves **alias → exact category slug → ordered `category_mapping`**.
- `CategoryMappingRepository.resolve_slug` gained `ORDER BY category_id`; with the exact-slug hit first, the ambiguous `restaurant` / nine shared-family buckets can no longer file a place at random.
- Migration `0009` adds `place.source_category varchar(120)` + `ix_place_source_category`; it is written on every imported row, resolved or not.
- The importer streams the CSV (`iter_acceslibre_rows`) and skips malformed rows; `load_acceslibre_file` stays a list wrapper for tests only. The CLI call site now passes the iterator.
- `import acceslibre --dry-run` prints `resolved/unresolved` plus up to 20 `unresolved: <value>=<count>` lines and rolls back; `--aliases` overrides the CSV path.
- `import report [--limit]` prints places per source and every unresolved `source_category`, exiting 1 while any remain — the DATA-02 gate that CI cannot run without the export.
- README and `docs/deploy.md` document the dataset origin and the dry-run → alias → import → report workflow.

## Task Commits

Both tasks are one logical change (migration, resolver, importer, CLI, tests, docs), committed once per the repo rule:

1. **Task 1 + Task 2** — `237c877` (feat) — `LET-33 feat(import): resolve Acceslibre categories through an auditable mapping`

## Files Created/Modified

- `migrations/versions/0009_place_source_category.py` — column + index, real `downgrade()`.
- `src/letmegetin/application/places/category_resolution.py` — `load_category_aliases`, `resolve_category`.
- `src/letmegetin/application/places/import_acceslibre.py` — `iter_acceslibre_rows`, streaming import, `source_category`, `resolved`/`unresolved` report, `dry_run`.
- `src/letmegetin/application/places/__init__.py` — exports the iterator; keeps the list wrapper.
- `src/letmegetin/admin.py` — `import acceslibre --aliases/--dry-run`, `import report`, `_run_admin(commit=…)`.
- `src/letmegetin/domain/places/entities.py` — `Place.source_category`.
- `src/letmegetin/domain/places/repositories.py` — `count_by_source`, `unresolved_categories`.
- `src/letmegetin/infrastructure/persistence/{models,mappers,repositories}.py` — column mirror, mapper, writes, deterministic `resolve_slug`, two report queries.
- `tests/unit/test_category_resolution.py` — 8 cases (alias hit, mapping fallback, exact-slug precedence, unknown, `None`, duplicate, gaps, committed CSV).
- `tests/integration/test_places_import.py` — resolution + raw value, dry-run, report exit 1→0, streaming proof; dedup fixture labels moved to the real vocabulary.
- `README.md`, `docs/deploy.md` — dataset origin and operator workflow.

## Verification (real output)

```
$ uv run ruff check .                              -> All checks passed!
$ uv run mypy                                      -> Success: no issues found in 71 source files
$ uv run bandit -r src -c pyproject.toml           -> 0 issues (Low 0, Medium 0, High 0)
$ uv run pytest -q --cov=letmegetin --cov-branch --cov-fail-under=85
220 passed, 1 warning in 30.36s — Total coverage: 92.64% (floor 85%)
```

Migration round-trip on `localhost:55433`:

```
$ uv run alembic downgrade -1   -> Running downgrade 0009 -> 0008
  ix_place_source_category|<none> ; source_category columns=0 ; alembic current = 0008
$ uv run alembic upgrade head   -> Running upgrade 0008 -> 0009
  ix_place_source_category|ix_place_source_category ; source_category columns=1 ; 0009 (head)
```

End-to-end on a 391-row fixture (one row per committed `activite` label):

```
$ ... import acceslibre --file <fixture> --dry-run
acceslibre import: created=391 linked=0 review=0 skipped=0 resolved=260 unresolved=131 dry_run=True
  unresolved: Accrobranche=1 … (20 shown)
exit=0 ; SELECT count(*) FROM place -> 0

$ ... import acceslibre --file <fixture>
acceslibre import: created=391 linked=0 review=0 skipped=0 resolved=260 unresolved=131 dry_run=False

$ ... import report --limit 5
places by source: acceslibre=391
Accrobranche=1
Acupuncture=1
Aéroport, aérodrome=1
…
unresolved total=131 across 131 source values
exit=1

SELECT category_id IS NOT NULL, count(*) FROM place WHERE source_id LIKE 'verify-%' GROUP BY 1
 -> f|260   t|131        # 0 of the 260 mapped labels unresolved, 131 known gaps named

# after deleting the fixture rows
$ ... import report
places by source: none
unresolved total=0 across 0 source values
exit=0
```

Integration fixture: `resolved=2`, `unresolved=1`, `unresolved: Château imaginaire=1`; `test-cat-1 → library`, `test-cat-2 → museum`, `test-cat-3 → NULL` with `source_category` set on all three.

## Decisions Made

- The alias CSV is the authority. `load_category_aliases` treats an empty target as a reviewed gap and only raises on an empty source or a duplicate slug.
- `resolve_category` takes both `CategoryRepository` and `CategoryMappingRepository`; the plan's prose required the exact-slug lookup but its first signature draft omitted the dependency.
- `--dry-run` does the reads (idempotency, candidate scoring) and rolls back explicitly: `_run_admin` gained `commit=False` so "never commits" is literal.
- `unresolved_categories()` returns the complete grouped list and the CLI applies `--limit` to the display, so `unresolved total` / `across m` stay true beyond 50 values.
- No route, no new dependency: stdlib `csv`/`json` and SQLAlchemy only.

## Deviations from Plan

1. **[Environment fact] Fixture labels use the real vocabulary.** The plan's draft assumed keys `bibliotheque`/`musee`; the committed CSV keys the measured 391 `activite` labels (`Bibliothèque médiathèque`, `Musée`). The fixtures and integration assertions use those labels (`musee` still resolves exactly as written). Inventing a `bibliotheque` alias would be curation — the operator's `user_setup` step — not executor work.
2. **[Environment fact] Empty alias rows are skipped, not rejected.** The file ships 131 deliberate gaps; the literal "`DomainError` on an empty side" would make the shipped file unloadable. Empty *source* and duplicate keys still raise.
3. **[Interface] `resolve_category` also takes a `CategoryRepository`.** Required to check the exact slug before the mapping, which the plan's signature draft omitted.
4. **[Interface] `unresolved_categories()` is uncapped; the CLI slices.** A SQL `LIMIT` would make the gate's totals undercount past 50 values.
5. **[Interface] `_run_admin(commit=False)`.** Added so `--dry-run` rolls back rather than committing an empty transaction.
6. **[Process] Committed on `main`, not a `LET-33-…` branch.** Same instruction conflict as 09-01: GSD runs with `branching_strategy: none` and wave 1 is on `main`; no branch was created.
7. **[Test fixture] The dedup fixture's `categorie` values moved to `Bibliothèque médiathèque`.** Dedup assertions are unchanged; leaving the invented `bibliotheque` would report a non-existent gap in every import output.

**Total deviations:** 7 (2 data-file facts, 3 interface drafts, 1 process, 1 fixture label).
**Impact on plan:** none on scope or acceptance; all six must-have truths hold against the committed vocabulary and the fixture.

## Issues Encountered

- `pre-commit`'s `ruff format` reflowed two test functions on the first commit attempt; re-staged and committed. No behavioural change.
- GitNexus' index is 27 commits behind HEAD (`staleness: behind`), so impact output was not trusted; call sites were verified by text search and the plan's measured list instead.

## Known Stubs

None. The 131 empty alias rows are reviewed data, not code stubs: they are the documented operator gaps that `import report` names.

## Threat Flags

None beyond the plan's register. The streaming path, the alias file and the CLI-only surface are covered by T-09-01/02/04; no secret, no new endpoint, no new dependency.

## Next Phase Readiness

- `09-03` can start: schema head is `0009`, and the fixture import already produces one `0.90+` link and one `0.60–0.90` review row it needs.
- It must: persist the review candidate (`duplicate_of_id`), add `duplicates list|merge|reject` with `place_review_decision`, add `coverage --format csv`, and keep both commands sane on an empty database (today: 0 places, prod and dev).
- It must not re-resolve categories: `place.source_category` and `category_id` are already written by this plan.
- Remaining human step: download the Acceslibre export, `--dry-run`, complete the 131 gaps in `data/referential/acceslibre_categories.csv`, import, `import report` → exit 0.

## Self-Check: PASSED

- `migrations/versions/0009_place_source_category.py` — FOUND
- `src/letmegetin/application/places/category_resolution.py` — FOUND
- `tests/unit/test_category_resolution.py` — FOUND
- commit `237c877` — FOUND (ancestor of HEAD)
- `0009` applies, downgrades and re-applies — VERIFIED

---
*Phase: 09-data-quality*
*Completed: 2026-11-05*
