---
phase: 13-documented-place-visualisation
plan: 02
subsystem: places
tags: [fastapi, ddd, postgres, batched-reads, next, tailwind, i18n, documentation-ladder]

# Dependency graph
requires:
  - phase: 13-documented-place-visualisation
    plan: 01
    provides: the D-01 ladder, Documentation, filled_rate and levelLabel
provides:
  - PlaceHit.documentation (an optional Documentation, None when nobody asked)
  - PlaceRepository.list_accessibility_for_places and CategoryGridRepository.get_for_slugs
  - search_places(with_documentation) — two batched reads, never N+1
  - GET /api/v1/places?with_documentation=true returning {rate, percent, level} per hit
  - --color-doc-sketch / -partial / -good / -very-good, light and dark
  - levelChipClass and levelDotClass in web/src/lib/documentation.ts
  - the search card's level marker (dot + name)
affects: [13-03 legend and family chips, 13-04 public API documentation]

actuals:
  tokens: 6737
  tasks: 3
  commits: 4
  plan_head_before: 8946e30b575bc3fc4966a3fd7ae0d5529882c349
  plan_head_after: 764a68379f748021659faf4c76793ee9d196ab86

tech-stack:
  added: []
  patterns:
    - "Two batched reads replace N+1: one grid read per distinct category, one values read per place id, then the shared filled_rate per hit"
    - "An absent optional field is left unset in the Pydantic model and omitted by response_model_exclude_unset, so the default payload keeps its old keys instead of gaining a null"
    - "The web owns a slug → class map beside the slug → label map: one source, two rendering contexts (chip, marker dot)"

key-files:
  created: []
  modified:
    - src/letmegetin/domain/places/entities.py
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/domain/referential/repositories.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/application/places/search.py
    - src/letmegetin/api/schemas/places.py
    - src/letmegetin/api/v1/places.py
    - tests/functional/places/test_places_search.py
    - web/src/lib/search.ts
    - web/src/lib/search.test.ts
    - web/src/lib/documentation.ts
    - web/src/lib/types.ts
    - web/src/app/globals.css
    - web/src/components/search/place-list.tsx

key-decisions:
  - "The two reads are bounded by the hit set, not by the page: the same SELECT count serves a 1-hit and a 100-hit search, and the test pins it at exactly two extra statements (T-13-03)."
  - "A hit with no category grid shortens the slug list, so `get_for_slugs` skips its query: the flag then costs one read, not two, and the payload is identical (rate 0.0, level none)."
  - "`documentation` is absent — not null — from the default search payload, via `response_model_exclude_unset` plus an unset field on the model; excluding nulls instead would have stripped category/address/lat/lng from every existing consumer."
  - "The search card marker is a 10px dot plus the level name in `text-muted`, deliberately not a pill: a pill in that row would read as a sibling of the amber 'Doublon possible' status."
  - "`get_for_slug` now delegates to `get_for_slugs`, so the single and batched projections cannot drift."

patterns-established:
  - "A batched repository method is added beside its single-row twin and reuses the same mapper, so the two shapes cannot diverge."
  - "An opt-in additive field is proved by a statement counter, not by a code review: `before_cursor_execute` counts the delta between the flag on and off for two page sizes."

requirements-completed: [PROD-01]

coverage:
  - id: S1
    description: "the flag is off by default: no `documentation` key in the payload, and the body stays a bare JSON array"
    requirement: PROD-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_places_search.py#test_search_omits_documentation_unless_asked"
        status: pass
      - kind: functional
        ref: "tests/functional/places/test_places_search.py#test_search_with_documentation_stays_a_bare_array"
        status: pass
    human_judgment: false
  - id: S2
    description: "with the flag, every hit carries {rate, percent, level}: a complete record, an undocumented place and a gridless place each get the ladder's answer"
    requirement: PROD-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_places_search.py#test_search_returns_documentation_when_asked"
        status: pass
    human_judgment: false
  - id: S3
    description: "an undocumented place is neither hidden nor de-ranked by its level (D-06)"
    requirement: PROD-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_places_search.py#test_search_keeps_an_undocumented_place"
        status: pass
    human_judgment: false
  - id: S4
    description: "the documentation reads are two SELECTs whatever the page size — no N+1"
    requirement: PROD-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_places_search.py#test_search_documentation_reads_do_not_scale_with_hits"
        status: pass
    human_judgment: false
  - id: S5
    description: "the search card shows the level as a dot + name marker, omitted when the field is absent"
    requirement: PROD-01
    verification:
      - kind: other
        ref: "cd web && npm run typecheck && npm run lint && npx vitest run"
        status: pass
    human_judgment: true
    rationale: "The rendered marker has no component test (there is none for this card today); the browser-facing proof is the e2e suite, which this plan does not run."

# Metrics
duration: 39min
completed: 2026-11-13
status: complete
---

# Phase 13 Plan 02: Search documentation Summary

**The search endpoint gains an opt-in `documentation: {rate, percent, level}` per hit, computed by exactly two batched reads over the hit set, and the search card renders the level as a decorative dot plus its name — never a pill, never a border tint.**

## Performance

- **Duration:** 39 min
- **Tasks:** 3 (4 commits: one task is TDD, so RED + GREEN)
- **Files modified:** 14
- **Gates:** `uv run pytest -q` → 401 passed; `uv run mypy` clean; `uv run ruff check . && ruff format --check .` clean; `web` typecheck + lint + `check:i18n` + vitest (67 passed)

## Accomplishments

- `PlaceHit` carries an optional `Documentation`, `None` meaning "the caller did not ask" — nothing is persisted (D-03).
- Two batched ports and their implementations: `PlaceRepository.list_accessibility_for_places(place_ids)` (one query joined to the criterion for its position, grouped in Python through the existing mapper) and `CategoryGridRepository.get_for_slugs(slugs)` (one query over `category_grid` joined on slug). Both use bound `.in_` parameters, never an interpolated IN list (T-13-04). `get_for_slug` now delegates to `get_for_slugs`, so the two projections cannot drift.
- `search_places(places, grids, …, with_documentation=False)` leaves the hits untouched when the flag is off. With it on, `_attach_documentation` collects the distinct category slugs, reads the grids and the values once each, and runs the shared `filled_rate` per hit; `Documentation.from_rate` turns the rate into the payload. A hit with no grid and a place with no recorded value both resolve to `rate 0.0` / `level none` and stay in the result set (D-06) — `values_by_place.get(id, [])` is what keeps that path total.
- The controller gained `with_documentation` (documented in the OpenAPI description), the grid repository dependency, and passes the hit's documentation into `PlaceSummaryOut.from_place`.
- `documentation` is **absent** — not `null` — from the default payload. The field existed since 13-01 and was serialised as `null`, which contradicted D-07; the model now leaves it unset and the route sets `response_model_exclude_unset=True`. Every other nullable key (`category`, `address`, `lat`, `lng`) is still explicitly set, so the response keeps exactly the keys it had.
- Web: four `--color-doc-*` tokens (light in `@theme`, dark in the `prefers-color-scheme` block); `levelChipClass`/`levelDotClass` beside `levelLabel`, all three sharing one `docLevel` lookup; `placesPath` always sends `with_documentation=true`; `PlaceSummary.documentation` is optional.
- The card renders a `inline-flex items-center gap-2 text-sm text-muted` marker holding an `aria-hidden` 10px dot and the level name. Selection, hover and border styles are untouched; the operating-status pill now shares a wrapping row with the marker.

## Task Commits

Each task was committed atomically:

1. **Task 1: batched accessibility and grid reads** — `303ba0f` (feat)
2. **Task 2 RED: the opt-in documentation contract** — `6fbe69b` (test)
3. **Task 2 GREEN: the two batched reads behind the flag** — `67c025e` (feat)
4. **Task 3: the level marker on the search card** — `764a683` (feat)

**Plan metadata:** this file, committed separately.

## TDD Record (Task 2, `tdd="true"`)

**RED** — `uv run pytest tests/functional/places/test_places_search.py -m functional -q -k "documentation or undocumented"` → `4 failed, 1 passed`:

- `test_search_omits_documentation_unless_asked` failed on `assert all("documentation" not in item …)` — the field was still serialised as `null`.
- `test_search_returns_documentation_when_asked` failed on the first comparison (`None != {"rate": 1.0, …}`).
- `test_search_keeps_an_undocumented_place` failed on `item["documentation"]` being `None`.
- `test_search_documentation_reads_do_not_scale_with_hits` failed on `assert (0 - 0) == 2`.
- `test_search_with_documentation_stays_a_bare_array` **passed at RED**: it guards an invariant that already held (the body was and remains a bare array), so it is a regression guard, not an assertion on the new behaviour.

Semantic assessment: every failing test failed on its own assertion about the planned behaviour — no import error, no collection error, no fixture crash.

**GREEN** — the same command → `22 passed`; the full suite → `401 passed`. The counting test now reports the delta as exactly 2 for both a 1-hit and a 100-hit search.

**REFACTOR** — none needed; the only post-GREEN change was `get_for_slug` delegating to `get_for_slugs`, folded into the GREEN commit (it is a two-line reduction, not a separate behaviour change).

## Decisions Made

- **Two reads, bounded by the hit set.** A page of 100 hits costs the same three SELECTs (list + grids + values) as a page of one; the functional test pins the delta at two and asserts it is identical for both page sizes.
- **A category-less hit set skips the grid read.** `get_for_slugs([])` returns `{}` without touching the database, so the flag costs one read instead of two when no hit has a category. That is strictly better than a wasted query, and the payload is unchanged (`rate 0.0`, `level none`).
- **Absent ≠ null.** Excluding nulls globally would have removed `category`/`address`/`lat`/`lng` from every existing consumer; `exclude_unset` removes only the field the caller did not set.
- **Marker, not pill.** The dot is `aria-hidden` and the level name is text, so colour never carries the level alone (D-08, D-10). The name also makes the card's accessible name include the level, as the UI-SPEC requires.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The `CategoryGridRepository` port lives in the referential context**
- **Found during:** Task 1
- **Issue:** The plan lists `src/letmegetin/domain/places/repositories.py` as the home of both new ports, but `CategoryGridRepository` is declared in `src/letmegetin/domain/referential/repositories.py`.
- **Fix:** `list_accessibility_for_places` was added to the places ports; `get_for_slugs` was added to the existing grid port in the referential file (and `Sequence` imported there).
- **Files modified:** `src/letmegetin/domain/referential/repositories.py`
- **Committed in:** `303ba0f`

**2. [Rule 1 - Bug] The default search payload carried `documentation: null`**
- **Found during:** Task 2 RED
- **Issue:** `PlaceSummaryOut.documentation` was declared in 13-01, so FastAPI serialised the key as `null` even without the flag — the must_have says absent by default (D-07), and "existing consumers pay nothing" is not true if every row grows a key.
- **Fix:** `PlaceSummaryOut.from_place` leaves the field unset when there is no documentation, and the `/places` route declares `response_model_exclude_unset=True`. Verified by test that `category`, `address`, `lat`, `lng` still appear (as `null`) exactly as before.
- **Files modified:** `src/letmegetin/api/schemas/places.py`, `src/letmegetin/api/v1/places.py`
- **Verification:** `test_search_omits_documentation_unless_asked` green; the detail endpoint's `documentation` is unaffected (`from_detail` sets it explicitly).
- **Committed in:** `67c025e`

**3. [Rule 3 - Blocking] `web/src/lib/types.ts` had to gain the optional field**
- **Found during:** Task 3
- **Issue:** `PlaceSummary` did not declare `documentation`, so the card could not read it without a cast. The plan's `files_modified` list omits this file.
- **Fix:** `documentation?: Documentation` on `PlaceSummary` (`PlaceDetail` already intersects it as required).
- **Files modified:** `web/src/lib/types.ts`
- **Committed in:** `764a683`

**4. [Rule 1 - Bug] The statement counter listened on the wrong engine**
- **Found during:** Task 2 GREEN
- **Issue:** Counting on `letmegetin.core.db.engine` reported zero SELECTs: the functional `client` fixture overrides `get_session` with `tests.db.SessionLocal`.
- **Fix:** the listener is attached to `tests.db.engine`, the engine the test client actually uses (as the plan specified). The assertion was not weakened — it still demands exactly two extra SELECTs.
- **Files modified:** `tests/functional/places/test_places_search.py`
- **Committed in:** `67c025e` (the RED commit already carried the assertion; only the listener target moved)

**5. [Rule 3 - Blocking] The 100-hit fixture had no category, so one of the two reads short-circuited**
- **Found during:** Task 2 GREEN
- **Issue:** the bulk rows were seeded without a category, so their slug set was empty and the delta was 1, not 2 — the test would have proven a shorter path than the one that runs in production.
- **Fix:** the 150 bulk rows now carry the `test-search-librairie` category (the one with the one-leaf grid), and the 1-hit case searches beta instead of alpha. Both scenarios now exercise the grid read and the values read. No assertion changed; no other test reads the bulk rows' category.
- **Files modified:** `tests/functional/places/test_places_search.py`
- **Committed in:** `67c025e`

---

**Total deviations:** 5 auto-fixed (3 blocking, 2 bugs)
**Impact on plan:** all five are mechanical consequences of the plan's intent; no scope creep. The plan's `files_modified` list was short by `web/src/lib/types.ts` and misattributed the grid port's file.

## Issues Encountered

- The development database (`letmegetin`) is behind the migrations (`place.source_license` missing), so ad-hoc requests against it fail. Every check in this plan ran against `letmegetin_test` through the functional suite, which is green.
- `gitnexus detect-changes --scope compare --base-ref 8946e30` reports 16 files / 52 symbols and `risk: high` — the flag is volume-driven (the whole phase diff) and the affected flows are exactly the ones this plan targets (`Search`, `Place_detail`, `PlaceList`, `HomePage → PlacesPath`). All gates are green.

## Known Stubs

None. `levelChipClass` has no consumer until 13-03 (legend and family chips) — it is an exported part of the ladder's single mapping, not a stub returning placeholder data.

## Threat Flags

None beyond the plan's model. The two new queries take their id/slug lists as bound `.in_` parameters (T-13-04 mitigated); both are bounded by the hit set, which is itself bounded by `limit ≤ 100` (T-13-03 accepted, now pinned by the counter test). `with_documentation` is coerced by FastAPI, so an invalid value is a 422.

## User Setup Required

None.

## Next Phase Readiness

- **13-03 can consume the tokens**: `--color-doc-sketch`, `--color-doc-partial`, `--color-doc-good`, `--color-doc-very-good` exist in light and dark; `doc-none`/`doc-complete` are deliberately absent (`none` uses `line`/`muted`, `complete` uses `accent`).
- **13-03 can consume the class maps**: `levelChipClass(slug)` and `levelDotClass(slug)` sit beside `levelLabel`, all sharing one `docLevel` lookup and returning `undefined` for an unknown slug. The chip map is unused so far — it exists for the family chips and the legend.
- **Search payload**: `PlaceSummary.documentation?` is optional in TS and absent from the JSON unless the flag is passed. Anything new that returns `PlaceSummaryOut` without the flag must also set `response_model_exclude_unset=True`, or it re-introduces the `null` key fixed here.
- **Legend bounds still have no API**: `DOCUMENTATION_LADDER` is domain-only; the UI-SPEC's Open Question 2 ("the server exposes the ladder") is still open for 13-03.
- **Not verified here**: the rendered marker has no component test and no 320 px visual check was taken (UI-SPEC backstop); the e2e suite in `letmegetin-e2e` is the browser-facing proof and was not run.

---

## Self-Check: PASSED
