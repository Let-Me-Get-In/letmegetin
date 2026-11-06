---
phase: 10-search-quality
plan: 02
subsystem: search
tags: [search, postgis, fastapi, openapi, breaking-change, filters]

# Dependency graph
requires:
  - phase: 10-search-quality
    provides: "10-01 category filter in the same `list_near` conditional chain and the same `search()` endpoint"
provides:
  - "`filters=a,b` narrows (AND): one indexed EXISTS per distinct criterion id instead of one `criterion_id IN (a,b)`"
  - "repeated criterion ids de-duplicated before predicate construction (`dict.fromkeys`)"
  - "regression tests: two ids intersect, one id unchanged, repeated id returns the same body"
  - "the AND semantics and the third-party migration note in `docs/public-api.md` and `docs/openapi.json`"
affects: [10.1, 11]

actuals:
  tokens: 2090
  tasks: 2
  commits: 1
  plan_head_before: 95e88212c91281d77013c1403c8149a661452ae9
  plan_head_after: 8732c0c0d4b5d0612e457820b315aee5bc9655f9

tech-stack:
  added: []
  patterns:
    - "Filter combination lives in the SQL predicate, not in a post-query merge: each criterion is a correlated `EXISTS` that probes `place_accessibility_pkey` on `(place_id, criterion_id)` and can short-circuit on the first miss."
    - "Semantic breaking changes are published in the contract diff: the OpenAPI `filters` description and `docs/public-api.md` carry the AND wording and the migration note."

key-files:
  created: []
  modified:
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/application/places/search.py
    - src/letmegetin/api/v1/places.py
    - tests/integration/test_places_search.py
    - docs/openapi.json
    - docs/public-api.md

key-decisions:
  - "One ANDed `EXISTS` per distinct id rather than `GROUP BY place_id HAVING count(*) = N`: N index probes short-circuit, the aggregate would sort every candidate in the radius before the distance ordering."
  - "De-duplicate with `dict.fromkeys(criterion_ids)`: order-preserving, no extra import, and a repeated id cannot amplify the subquery count (T-10-05)."
  - "Keep the parameter name and type unchanged; document the behaviour change in the contract instead of introducing a new parameter or a `/v2`."

requirements-completed: [SEARCH-01]

coverage:
  - id: D1
    description: "Two criterion ids return only the places that hold both; the single-id request is byte-identical to before; a repeated id returns the same body."
    requirement: SEARCH-01
    verification:
      - kind: integration
        ref: "tests/integration/test_places_search.py#test_search_and_combines_two_criteria"
        status: pass
      - kind: integration
        ref: "tests/integration/test_places_search.py#test_search_single_criterion_is_unchanged"
        status: pass
      - kind: integration
        ref: "tests/integration/test_places_search.py#test_search_dedupes_repeated_criterion_ids"
        status: pass
    human_judgment: false
  - id: D2
    description: "The narrowing semantics are on the published contract (`docs/openapi.json` description + `docs/public-api.md` migration note)."
    requirement: SEARCH-01
    verification:
      - kind: other
        ref: "uv run python scripts/export_openapi.py (sha1 stable across two runs: 6abc109e8361ceb8e8877c576031a31e0c7057fb)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-11-06
status: complete
---

# Phase 10 Plan 02 Summary

**`filters=a,b` now intersects instead of unioning: one indexed EXISTS per distinct criterion id, ANDed, with regression tests and a plain migration note on the public contract**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-11-06T00:35:11Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- `GET /api/v1/places?filters=8,12` returns only places holding **both** criteria. Before this plan the predicate was a single `EXISTS (... criterion_id IN (8,12))`, i.e. a union: adding a criterion widened the result set, the opposite of a filter.
- A single criterion returns exactly what it returned before (same single `EXISTS` shape, same index probe); the plan's one-criterion guarantee is covered by its own test.
- A repeated id (`filters=7,7`) collapses to one predicate via `dict.fromkeys`, so the request cannot amplify the subquery count.
- `docs/public-api.md` gains a "Combining filters" subsection: AND narrows, one example URL, and the migration note for consumers that relied on the old OR (one request per criterion, or union the `slug` lists client-side).
- `docs/openapi.json` regenerated: the only diff is the `filters` description (query parameter and its schema), byte-stable on a second export.

## Task Commits

One commit per plan (repo rule), not per task:

1. **Plan 10-02** — `8732c0c` (fix)

## Files Created/Modified

- `src/letmegetin/infrastructure/persistence/repositories.py` — `list_near`: loop of one `EXISTS` per `dict.fromkeys(criterion_ids)`, chained with `.where` so SQLAlchemy ANDs them; `shortcut:` comment records the value-semantics limit.
- `src/letmegetin/application/places/search.py` — `search_places` docstring states that multiple criteria narrow.
- `src/letmegetin/api/v1/places.py` — `filters` description: "a place must match every id (AND)"; name, type and `_criterion_ids` untouched.
- `tests/integration/test_places_search.py` — `test-search-delta` fixture (45.10/5.0, ≈11 km out, holds both criteria) seeded outside `_PLACES`; three new tests; the fixture keeps the exact expected lists of the radius/sort tests intact.
- `docs/openapi.json` — regenerated snapshot (2 lines changed).
- `docs/public-api.md` — "Combining filters" subsection with the behaviour-change note.

## Decisions Made

- Correlated `EXISTS` per criterion, not `GROUP BY ... HAVING count(*) = N`: at 634k places the aggregate sorts the whole match set before the distance ordering; N probes on `place_accessibility_pkey` stop at the first missing criterion.
- Keep the query parameter unchanged and publish the semantic change in the contract, because the second consumer (the web client) sends multiple ids and does want the intersection.
- Value semantics stay "a value exists", as recorded in the `shortcut:` comment: whether `entrance = no` should match "step-free entrance" is a separate product decision (not SEARCH-01).

## Deviations from Plan

None - plan executed exactly as written. The plan's frontmatter `files_modified` omits `docs/public-api.md`, but its Task 2 explicitly edits it; six files were committed, which is the task's file set.

Repository-rule note: the plan says to work on a `LET-34-…` branch. 10-01 had landed directly on `main` (`95e8821`), so this plan ran on `LET-34-search-and-filters` created from that commit — the equivalent of "rebased on the 10-01 branch". Nothing pushed.

## Issues Encountered

- **Port 8000 remains occupied** by an unrelated local app, so the live check used `uvicorn letmegetin.main:app --port 8001` against the dev PostGIS (634 931 places, 1 711 095 accessibility rows). The process was stopped afterwards; 8001 is free.
- **Local baseline unchanged.** Exactly the five failures recorded in `STATE.md` "Known debt" (three search tests that assume the `place` table holds only fixtures, one duplicates/coverage test, one import-report test). The three new tests pass, including against the national dataset.
- **GitNexus index is 40 commits behind HEAD**, so `impact list_near` returned `UNKNOWN`; confirmed by text search: two call sites (`application/places/search.py`, domain port). `detect-changes --scope all` reports risk `medium` with a single affected flow, `Search → List_near`, which is the intended change. The extra `list_reviews`/`list_photos` entries are class-level re-indexing noise.

## Verification Output

```
uv run ruff check .                    → All checks passed!
uv run ruff format --check .           → 188 files already formatted
uv run mypy                            → Success: no issues found in 73 source files
uv run bandit -r src -c pyproject.toml → High: 0, Medium: 0, Low: 0
uv run pytest tests/integration/test_places_search.py -q
                                       → 3 failed, 11 passed (3 known baseline + 3 new pass)
uv run pytest -q --cov=letmegetin --cov-branch --cov-fail-under=85
                                       → 5 failed, 233 passed; coverage 92.47% (floor 85%)
                                         failures = the five known baseline ones only
export_openapi.py twice                → identical sha1 (6abc109e…), 2 lines changed
```

Negative proof (predicate temporarily reverted to `criterion_id.in_(...)`):

```
uv run pytest tests/integration/test_places_search.py -q -k "and_combines"
    → 1 failed, 13 deselected  (test_search_and_combines_two_criteria)
```

OpenAPI diff:

```diff
-            "description": "Comma-separated criterion ids",
+            "description": "Comma-separated criterion ids; a place must match every id (AND)",
```

Live check on the national dataset (`localhost:8001`, `lat=48.8566&lng=2.3522&radius=150`,
dev PostGIS — criteria 8 = `entree-ouverture-de-porte`, 12 = `entree-obstacles-a-la-porte-d-entree`):

```
filters=8     -> 3 results
filters=12    -> 5 results
filters=8,12  -> 2 results        (AND: fewer than either alone)
old OR shape  -> 6 results        (3 + 5 - 2 union, before the fix)
```

## Next Phase Readiness

- **10.1 (SEARCH-03, pagination)** extends the same `list_near` ordering: it must add a stable tie-breaker to `order_by(distance)`. The per-criterion `EXISTS` loop sits before `family`/`category` in the conditional chain and does not constrain ordering.
- **10.1** also changes the `placesPath` / `limit` contract in `web/src/lib/search.ts`; `filters` is still built by `criteria.join(",")` and now means intersection, so the UI needs no change for this semantic.
- **Phase 11** e2e should tick two criteria in the UI and assert a *subset* of the single-criterion request — the manual dev-host check from the plan's verification list is still outstanding.
- The `docs/public-api.md` migration paragraph is the contractual record for third parties; nothing else needs publishing for SEARCH-01.

---

*Phase: 10-search-quality*
*Completed: 2026-11-06*

## Self-Check: PASSED

All six claimed files exist in commit `8732c0c`; the commit is an ancestor of HEAD.
