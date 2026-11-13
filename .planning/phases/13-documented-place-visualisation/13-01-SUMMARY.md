---
phase: 13-documented-place-visualisation
plan: 01
subsystem: places
tags: [fastapi, pydantic, ddd, domain, next, i18n, accessibility, documentation-ladder]

# Dependency graph
requires:
  - phase: 12-licence-provenance
    provides: place detail endpoint, accessibility values and the category grid already in place
provides:
  - domain/places/documentation.py — the D-01 ladder (six slugs, integer bounds, half-up percent)
  - Documentation dataclass {rate, percent, level} on PlaceDetail
  - DocumentationOut {rate, percent, level} on the detail response
  - corrected filled_rate denominator (answerable criteria, 19 on category 1)
  - family rates divided by their own grid leaves, absent families omitted
  - web levelLabel(slug) mapping the six slugs to fr/en labels
affects: [13-02 search documentation, 13-03 legend and family levels]

actuals:
  tokens: 8258
  tasks: 2
  commits: 2
  plan_head_before: db2684840b15496660fb682b2abe614b19404be7
  plan_head_after: 9803d4bb2ab3a0e54fd2b0b5f51fa622612a1dc2

tech-stack:
  added: []
  patterns:
    - "One integer decides both: percent = floor(rate*100 + 0.5), then the D-01 bounds decide the slug, so the printed percent and the level cannot disagree"
    - "The server owns the ladder; the web maps a slug to an i18n label and never re-derives a level (D-02)"
    - "Answerable criteria, not grid leaves: array groups and option values are excluded from the denominator; an option under an array group counts"

key-files:
  created:
    - src/letmegetin/domain/places/documentation.py
    - tests/unit/domain/places/test_documentation.py
    - web/src/lib/documentation.ts
    - web/src/lib/documentation.test.ts
  modified:
    - src/letmegetin/application/places/get_place.py
    - src/letmegetin/api/schemas/places.py
    - src/letmegetin/api/v1/places.py
    - web/src/lib/types.ts
    - web/src/lib/i18n.ts
    - web/src/app/places/[slug]/page.tsx
    - tests/unit/application/places/test_place_detail.py
    - tests/functional/places/test_places_search.py
    - tests/functional/places/test_places_reviews.py

key-decisions:
  - "The ladder switches on a clamped whole percent, never on a float threshold: 0.995 prints 100 and is therefore `complete`, not `very_good` beside a 100 % bar (D-01, UI-SPEC rounding rule)."
  - "The denominator is the grid's answerable criteria (no `array` groups, no option's own values), which makes the ladder reachable: category 1 scores 8/19 = 0.421 instead of 8/2 (D-12)."
  - "Family rates divide by that family's leaves in the same grid and a family with no leaf is omitted, so `visuel`/`auditif`/`mental` read as “Non renseigné” instead of a false 0 % (D-12)."
  - "`get_place` no longer takes the criterion repository: the grid tree carries the same `handicap_families`, so the criteria query per detail request was dead weight after the family fix."

patterns-established:
  - "A derived enum ships its own integer (`percent`) in the payload so the client cannot re-round it into disagreement with the level."
  - "The web's documentation module is a slug → message-key map (mirrors `FAMILY_KEYS`/`familyLabel`), with an `undefined` branch for an unknown enum so the page degrades to the percent sentence."

requirements-completed: [PROD-01]

coverage:
  - id: D1
    description: "the detail response carries documentation {rate, percent, level}, the level derived from the printed integer percent"
    requirement: PROD-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_places_search.py#test_place_detail_returns_the_accessibility_skeleton"
        status: pass
      - kind: functional
        ref: "tests/functional/places/test_places_reviews.py#test_place_detail_returns_the_tree_values_and_completion"
        status: pass
      - kind: unit
        ref: "tests/unit/application/places/test_place_detail.py#test_get_place_carries_the_documentation_level_of_its_filled_rate"
        status: pass
    human_judgment: false
  - id: D2
    description: "the ladder is total over every rate: 0.0 none, 0.005 sketch, 0.255 partial, 0.505 good, 0.755 very_good, 0.995 complete"
    requirement: PROD-01
    verification:
      - kind: unit
        ref: "tests/unit/domain/places/test_documentation.py (bounds table, gap rates, half-up rounding, DOCUMENTATION_LADDER ↔ documentation_level lockstep)"
        status: pass
    human_judgment: false
  - id: D3
    description: "the record page shows the level name as h3#doc-overall and announces “{level}, N %” on the progress bar, printing the server percent verbatim"
    requirement: PROD-01
    verification:
      - kind: unit
        ref: "web/src/lib/documentation.test.ts (six slugs labelled in fr and en, unknown slug → undefined)"
        status: pass
      - kind: other
        ref: "cd web && npm run typecheck && npm run lint && npx vitest run"
        status: pass
    human_judgment: true
    rationale: "The rendered heading and aria-valuetext are not asserted by a component test; the browser-facing proof is the e2e suite, which this plan does not run."

# Metrics
duration: 4min
completed: 2026-11-13
status: complete
---

# Phase 13 Plan 01: Documented-place visualisation tracer Summary

**The D-01 documentation ladder lands server-side as one integer percent and six slugs, the detail endpoint serialises `documentation: {rate, percent, level}`, and the record page renders the level name as text with `aria-valuetext` — the web holds no rate→level logic.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-13T22:36:01Z
- **Completed:** 2026-11-13T22:39:45Z
- **Tasks:** 2
- **Files modified:** 13 (4 created)

## Accomplishments

- `src/letmegetin/domain/places/documentation.py` is pure domain: `DocumentationLevel`, `DOCUMENTATION_LEVELS`, `DOCUMENTATION_LADDER` (the D-01 display bounds as whole percentages), `documentation_level(percent)`, `percent_of(rate)` and the frozen `Documentation` dataclass. `percent = floor(rate*100 + 0.5)` is computed once and the level switches on that same integer, so `0.995 → 100 → complete` and no page can print "100 %" beside a `very_good` level.
- The three completion helpers (`recorded`, `leaf_slugs`, `filled_rate`) moved out of `get_place.py` into the domain module, so 13-02's batched search computation shares the identical numerator and denominator.
- **Denominator fixed (D-12):** `leaf_slugs` now returns the *answerable* criteria — `array` groups skipped, option children skipped, an option criterion under an array parent counted. Category-1 grids therefore divide by 19 criteria, not 2, and the three middle bands of the ladder become reachable.
- **Family rates fixed (D-12):** `_completion_by_family` takes the grid leaves with their `handicap_families` and divides by the family's own leaves; a family with no leaf is omitted rather than reported as `0.0`.
- `PlaceDetail` carries `documentation`; `PlaceSummaryOut.documentation` exists but stays `None` (the search flag is 13-02); `PlaceDetailOut.from_detail` fills it with `DocumentationOut(rate, percent, level)`.
- Web: `types.ts` gains `Documentation` and `PlaceDetail.documentation`; `i18n.ts` gains the six level labels and `docValueText` in fr and en; `documentation.ts` exports `DOC_LEVELS` and `levelLabel`, returning `undefined` for an unknown slug; the record page renders `h3#doc-overall`, keeps `aria-valuenow` and adds `aria-valuetext` "{level}, N %", and prints `documentation.percent` verbatim (`Math.round(filled_rate * 100)` is gone).

## Task Commits

Each task was committed atomically:

1. **Task 1: Ladder + overall documentation on the detail endpoint** — `724ad83` (feat)
2. **Task 2: Record page renders the overall level from the slug** — `9803d4b` (feat)

**Plan metadata:** this file, committed separately.

## Files Created/Modified

- `src/letmegetin/domain/places/documentation.py` — ladder, `Documentation`, `percent_of`, `recorded`, `answerable_criteria`, `leaf_slugs`, `filled_rate`
- `src/letmegetin/application/places/get_place.py` — builds `documentation` from `filled_rate`, family rates from the grid leaves, criterion repository dropped
- `src/letmegetin/api/schemas/places.py` — `DocumentationOut`, `PlaceSummaryOut.documentation`, `from_detail` wiring
- `src/letmegetin/api/v1/places.py` — `get_place(places, grids, slug)` at the two call sites; the detail endpoint's unused `CriterionRepo` dependency removed
- `web/src/lib/types.ts` — `Documentation`, `PlaceDetail.documentation`
- `web/src/lib/i18n.ts` — `docNone` … `docComplete`, `docValueText` (fr + en)
- `web/src/lib/documentation.ts` — `DOC_LEVELS`, `levelLabel`
- `web/src/app/places/[slug]/page.tsx` — level heading, `aria-valuetext`, server percent
- `tests/unit/domain/places/test_documentation.py`, `tests/unit/application/places/test_place_detail.py`, `web/src/lib/documentation.test.ts` — ladder, wiring and label coverage
- `tests/functional/places/test_places_search.py` — beta now owns a one-leaf grid, so the endpoint is exercised end to end (`complete`, family `moteur` only)
- `tests/functional/places/test_places_reviews.py` — asserts `documentation` for the 0.5 fixture

## Decisions Made

- **The ladder switches on a clamped integer**, not on float thresholds — a second float ladder would let the printed percent and the slug disagree at the edges.
- **`percent_of` clamps to [0, 100]** before the level lookup, so a rate slightly outside [0, 1] still yields a total mapping.
- **Family omission instead of `0.0`** — "no criterion to answer" is not "not documented"; the UI's `notProvided` branch becomes reachable.
- **`get_place` lost its `criteria` parameter** — after the family fix the grid tree carries the same `handicap_families`, so the per-request `list_all()` was dead weight.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Functional fixtures assumed the old criterion-table family rates**
- **Found during:** Task 1, running the functional suite
- **Issue:** `test_place_detail_returns_the_accessibility_skeleton` asserted `accessibility_by_family["visuel"] == 0.0` for a place with **no category grid at all**; with the corrected denominator that place has no leaves, so every family is absent and the assertion raised `KeyError`.
- **Fix:** beta now gets its own category and a one-leaf grid (`test-search-step`, `moteur`), which upgrades the test from a vacuous `0.0` to the real ladder path: `documentation == {rate: 1.0, percent: 100, level: "complete"}`, `accessibility_by_family == {"moteur": 1.0}` and `"visuel"` absent.
- **Files modified:** `tests/functional/places/test_places_search.py`
- **Verification:** `uv run pytest tests/functional/places/test_places_search.py -q` → green; full suite 396 passed.
- **Committed in:** `724ad83`

**2. [Rule 1 - Bug] The detail endpoint asked the criterion table for families it no longer used**
- **Found during:** Task 1
- **Issue:** `get_place(places, criteria, grids, slug)` still took the criterion repository after `_completion_by_family` moved to grid leaves; it was a dead DB query on every detail request (and the endpoint's `CriterionRepo` dependency existed only for it).
- **Fix:** signature is now `get_place(places, grids, slug)`; both call sites and the detail endpoint dependency updated. `write_accessibility` keeps `CriterionRepo` (it passes it to `contribute`).
- **Files modified:** `src/letmegetin/application/places/get_place.py`, `src/letmegetin/api/v1/places.py`, `tests/unit/application/places/test_place_detail.py`
- **Verification:** `uv run mypy` → clean; full suite green.
- **Committed in:** `724ad83`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both follow from the D-12 denominator fix the plan mandates; no scope creep. The plan's `files_modified` list did not name `src/letmegetin/api/v1/places.py`, which had to change for the signature.

## Issues Encountered

None beyond the two deviations.

## Known Stubs

None. `PlaceSummaryOut.documentation` defaults to `None` by design — the search opt-in is 13-02.

## User Setup Required

None.

## Next Phase Readiness

- 13-02 can batch-compute the search documentation: `filled_rate`, `leaf_slugs` and `Documentation.from_rate` are importable domain functions, and `PlaceSummaryOut.documentation` is already declared so only the query and the flag remain.
- 13-03 can add per-family levels: `accessibility_by_family` already uses the shared denominator and omits absent families; only the `{rate, level}` shape and the UI chips are left.
- The web's `levelLabel` deliberately returns `undefined` for unknown slugs — 13-02/13-03 must render nothing rather than guess in that branch.
- Not verified here: the rendered heading and `aria-valuetext` have no component test; the e2e suite (separate repo) is the browser-facing proof, and this plan does not run it.

---

## Self-Check: PASSED
