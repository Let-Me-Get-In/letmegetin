---
phase: 13-documented-place-visualisation
plan: 03
subsystem: places
tags: [fastapi, pydantic, openapi, next, i18n, accessibility, documentation-ladder]

# Dependency graph
requires:
  - phase: 13-documented-place-visualisation
    plan: 01
    provides: the D-01 ladder, Documentation, filled_rate, levelLabel, the overall level
  - phase: 13-documented-place-visualisation
    plan: 02
    provides: the search flag, the doc colour tokens, levelChipClass and levelDotClass
provides:
  - accessibility_by_family carrying {rate, percent, level} per family (get_place + schema)
  - documentation_ladder on the detail response — the six {slug, min, max} bounds, server-owned
  - the six-entry legend, read from the served ladder and never from a local table
  - the empty-record banner that replaces the completion section, link omitted without a grid
  - docs/public-api.md "Documentation" section and the regenerated docs/openapi.json
  - docBoundsRange / docBoundsExact i18n keys (fr + en)
affects: [phase verification, letmegetin-e2e copy selectors]

actuals:
  tokens: 8197
  tasks: 3
  commits: 3
  plan_head_before: 1152a8da0a1cad173c3b50075050115140bdd986
  plan_head_after: 491d435f8360ccbb7f91071eef016c1988725812

tech-stack:
  added: []
  patterns:
    - "A published contract renders itself from the domain tuple: the OpenAPI bounds string is built from DOCUMENTATION_LADDER, so a renumbered rung changes the docs automatically and the test loops the same tuple"
    - "The web orders the legend by its declared DOC_LEVELS and takes every bound from the payload; a rung the server does not serve is skipped, never guessed"
    - "One level map, three rendering contexts: levelChipClass for the family chips, levelDotClass for the legend swatch (its `none` branch is already the dashed muted ring the UI-SPEC asks for)"

key-files:
  created: []
  modified:
    - src/letmegetin/application/places/get_place.py
    - src/letmegetin/api/schemas/places.py
    - tests/unit/application/places/test_place_detail.py
    - tests/functional/places/test_places_search.py
    - tests/integration/api/test_openapi.py
    - docs/openapi.json
    - docs/public-api.md
    - web/src/lib/types.ts
    - web/src/lib/i18n.ts
    - web/src/lib/documentation.ts
    - web/src/lib/documentation.test.ts
    - web/src/app/places/[slug]/page.tsx

key-decisions:
  - "The OpenAPI bounds text is generated from DOCUMENTATION_LADDER and interpolated into both detail properties, so the published contract cannot drift from the derivation while still naming every rung."
  - "The legend lives in its own section after the completion block, not inside it: on a `none` record the completion section disappears, and the legend must survive it."
  - "Two new i18n keys (docBoundsRange, docBoundsExact) carry the legend's bounds copy: the single-value case (0 %, 100 %) would otherwise need a French literal in the component, and the no-break space convention belongs in the dictionary."
  - "A family the web cannot label is rendered as the family name alone rather than `notProvided`: an unknown enum must not be reported as undocumented."
  - "The banner link is gated on `place.tree.length > 0`, not on a separate `noTree` flag: an empty tree is exactly the case where #contribute would be a dead end."

patterns-established:
  - "A server-owned ladder ships with the payload that uses it; the client holds only the order, the labels and the class maps."
  - "An empty state replaces the section it makes meaningless instead of adding a zeroed copy of it beside the explanation."

requirements-completed: [PROD-01]

coverage:
  - id: F1
    description: "accessibility_by_family carries {rate, percent, level} per family, derived from the same ladder and the same grid-leaf denominator as the overall level"
    requirement: PROD-01
    verification:
      - kind: unit
        ref: "tests/unit/application/places/test_place_detail.py#test_family_rates_divide_by_their_own_leaves_and_omit_absent_families"
        status: pass
      - kind: functional
        ref: "tests/functional/places/test_places_search.py#test_place_detail_returns_the_accessibility_skeleton"
        status: pass
    human_judgment: false
  - id: F2
    description: "documentation_ladder returns the six server-owned {slug, min, max} rungs, and the legend renders all six from that payload"
    requirement: PROD-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_places_search.py#test_place_detail_returns_the_accessibility_skeleton (ladder equals the six bounds)"
        status: pass
      - kind: unit
        ref: "web/src/lib/documentation.test.ts (bounds read from the served ladder, declared order kept, missing rung skipped)"
        status: pass
    human_judgment: true
    rationale: "The rendered list has no component test; the module that feeds it is covered. The 320 px wrap is a visual backstop the UI-SPEC records, not an assertion."
  - id: F3
    description: "an undocumented record replaces the completion section with the banner and drops the link when the place has no criteria grid"
    requirement: PROD-01
    verification:
      - kind: other
        ref: "cd web && npm run typecheck && npm run lint && npx vitest run"
        status: pass
    human_judgment: true
    rationale: "Server-rendered JSX with no component test in this repo; the e2e suite is the browser-facing proof and was run against the deployed environment, which predates this change."
  - id: F4
    description: "a family absent from accessibility_by_family renders the notProvided text with no chip"
    requirement: PROD-01
    verification:
      - kind: unit
        ref: "tests/unit/application/places/test_place_detail.py (absent family omitted from the map)"
        status: pass
      - kind: other
        ref: "FAMILY_KEYS.map in page.tsx: familyDoc undefined → notProvided branch, no chip"
        status: pass
    human_judgment: true
    rationale: "The rendered dd has no component test; the payload branch that drives it is asserted."
  - id: F5
    description: "docs/public-api.md and the OpenAPI description document with_documentation, the six slugs and bounds, and the {rate, percent, level} shapes"
    requirement: PROD-01
    verification:
      - kind: integration
        ref: "tests/integration/api/test_openapi.py#test_openapi_documents_the_documentation_contract (loops DOCUMENTATION_LADDER)"
        status: pass
      - kind: other
        ref: "python doc parser over docs/public-api.md: header, six rows, flag and percent present"
        status: pass
    human_judgment: false

# Metrics
duration: 27min
completed: 2026-11-13
status: complete
---

# Phase 13 Plan 03: Documented-place visualisation completion Summary

**Every family now carries its own documented level on the served ladder, the record page renders the six-rung legend from the bounds the API ships instead of a local table, an empty record replaces the completion section with a banner, and the public contract documents the flag, the ladder and the breaking family shape.**

## Performance

- **Duration:** ~27 min
- **Tasks:** 3
- **Files modified:** 12 (none created)
- **Gates:** `uv run pytest -q` → 402 passed; `uv run mypy` clean; `uv run ruff check . && ruff format --check .` clean; `uv run python scripts/export_openapi.py` → no drift; web `typecheck` + `lint` (incl. `check:i18n`, 30 files) + vitest 71 passed; docs ladder parser green

## Accomplishments

- `get_place` returns `accessibility_by_family: dict[str, Documentation]`; `_completion_by_family` keeps the per-family grid-leaf denominator and now wraps each rate in `Documentation.from_rate`, so a family percent and its slug are the same integer by construction.
- `PlaceDetailOut` gains `DocumentationLevelOut` and `documentation_ladder`, populated straight from `DOCUMENTATION_LADDER` in `from_detail` — `none` is `(0, 0)`, `complete` is `(100, 100)`. `accessibility_by_family` is now `dict[str, DocumentationOut]`, all three fields copied from the domain object.
- The published contract describes itself: `_LADDER_SHAPE` interpolates every `(slug, min, max)` triple into both detail properties from the domain tuple, and `test_openapi_documents_the_documentation_contract` loops the same tuple (a wrong bound on any rung fails), asserts the "stable enum, not display text" statement, the `{rate, percent, level}` family shape, the `DocumentationLevelOut` keys and a non-empty `with_documentation` description.
- `docs/openapi.json` regenerated (byte-identical across two exports) and `docs/public-api.md` gains a **Documentation** section: the six-row `| Level | Min % | Max % |` table, the three field shapes, `percent` as the server's own integer, the opt-in flag and the `accessibility_by_family` breaking change. The `/places` and `/places/{slug}` table rows were updated.
- Record page: `h2#completion` is now a muted Body label with the legend intro above the level, `h3#doc-overall` is the anchor, the percent sentence prints once, the bar keeps `aria-valuenow`/`aria-valuetext` and gains the `ring-1 ring-inset ring-muted` track, and the four family chips iterate `FAMILY_KEYS` showing the level name only. A family missing from the payload reads `notProvided` with no chip.
- The legend is a `h3#doc-legend` + `ul` of six `li`s (aria-hidden swatch, name 600, bounds from the payload); on `level === "none"` the banner (`section#doc-undocumented`, plain paper surface, `space-y-2`) replaces the whole completion section and links to `#contribute` only when the tree is non-empty — and the legend still renders below it.
- `web/src/lib/documentation.ts` gains `levelBounds` and `legendEntries`; `documentation.test.ts` feeds them flipped and partial ladders to prove the order comes from `DOC_LEVELS` and the numbers from the server.

## Task Commits

Each task was committed atomically:

1. **Task 1: ladder + per-family levels on the detail response** — `f92cd7b` (feat, breaking)
2. **Task 2: family chips, legend and empty-record banner** — `9dbd9ef` (feat)
3. **Task 3: the public contract** — `491d435` (docs)

**Plan metadata:** this file, committed separately.

## Files Created/Modified

- `src/letmegetin/application/places/get_place.py` — family map is `dict[str, Documentation]`
- `src/letmegetin/api/schemas/places.py` — `DocumentationLevelOut`, `documentation_ladder`, family `DocumentationOut`, `_LADDER_SHAPE` from `DOCUMENTATION_LADDER`
- `tests/unit/application/places/test_place_detail.py` — family asserts the dataclass, not a float
- `tests/functional/places/test_places_search.py` — family `{rate, percent, level}` + the six ladder rows
- `tests/integration/api/test_openapi.py` — the contract test that loops the ladder
- `docs/openapi.json` — regenerated (also picks up 13-01/13-02's undocumented fields)
- `docs/public-api.md` — Documentation section, endpoints table rows
- `web/src/lib/types.ts` — `PlaceDetail.accessibility_by_family` object shape + `documentation_ladder`
- `web/src/lib/i18n.ts` — legend, banner and bounds keys (fr + en); `criteriaHaveValue` no-break space; `reviewCountLine` percent clause removed
- `web/src/lib/documentation.ts` — `levelBounds`, `legendEntries`
- `web/src/lib/documentation.test.ts` — legend-bounds coverage
- `web/src/app/places/[slug]/page.tsx` — hierarchy, chips, legend, banner

## Decisions Made

- **The bounds text is generated, not copied.** `_LADDER_SHAPE` is built from `DOCUMENTATION_LADDER` and used by both detail properties, so the plan's "both descriptions name every rung" holds without a second hand-written table that could drift.
- **The legend is its own section.** The UI-SPEC lists it as step 7 inside the completion section, but the empty-record rule says the section disappears and the legend stays; a sibling section is the only structure that satisfies both, and the heading order stays `h2` → `h3`.
- **`levelDotClass` draws the swatches.** Its `none` branch is already `border border-dashed border-muted`, exactly the swatch the UI-SPEC specifies, and its other branches are the chip backgrounds — one map instead of a third.
- **Two new i18n keys for bounds.** `docBoundsRange` (`{min}–{max} %` / `{min}–{max}%`) and `docBoundsExact` (`{percent} %` / `{percent}%`) keep the no-break-space convention and the `none`/`complete` single-value case out of the component.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `docs/openapi.json` was stale and CI checks it byte-for-byte**
- **Found during:** Task 1, after the schema change
- **Issue:** `scripts/export_openapi.py` regenerates the snapshot and `.github/workflows/ci.yml` runs `git diff --exit-code docs/openapi.json`. The committed snapshot carried neither 13-01's `documentation` object nor 13-02's `with_documentation` parameter — the branch was already drifting — so the Task 1 export necessarily includes all three plans' schema changes.
- **Fix:** regenerated with the repo's own script (never hand-edited) and proved deterministic: two exports byte-identical.
- **Files modified:** `docs/openapi.json`
- **Verification:** `uv run python scripts/export_openapi.py && git diff --exit-code docs/openapi.json` → no diff.
- **Committed in:** `f92cd7b`

### Planned-content additions

**2. Two i18n keys the UI-SPEC's key table does not name** — `docBoundsRange`, `docBoundsExact`. Without them the legend's bounds would be a French literal inside the component (the `check:i18n` gate exists for that) or a normal space where the copy contract mandates a no-break space. Both fr and en added; parity is enforced by the `Messages` type.

**3. The legend sits in its own `<section aria-labelledby="doc-legend">` after the conditional completion block** rather than as the last child of `section#completion` (UI-SPEC layout step 7): the empty-record rule requires the legend to survive that section's removal. Same visual order, same `h3`/`ul` markup.

**4. The legend swatch uses `levelDotClass`, not `levelChipClass`** — the chip map's `none` entry is `border border-line`, while the UI-SPEC asks the `none` swatch for a dashed 1px muted ring; the dot map already is that, and the tinted entries carry the same backgrounds.

### Cross-repo (`letmegetin-e2e`)

**5. No selector needed changing.** The plan expected the two edited literals to be text-selected by the e2e suite; `grep` over `tests/**/*.ts` finds no match for `criteriaHaveValue` (`… ont une valeur`) or `reviewCountLine` (`… avis · … de la fiche renseignée`), so the sibling checkout is untouched. The suite was still run as the plan asks: `E2E_BASE_URL=https://app.dev.letmegetin.org npx playwright test --grep "record|search" --project=chromium` → **10 passed**. That run executes against the deployed app, which predates this change, so it proves the suite still matches today's product, not that it matches the new copy.

---

**Total deviations:** 1 auto-fixed (blocking, generated snapshot) + 3 planned-content additions + 1 cross-repo finding.
**Impact on plan:** no scope creep; the snapshot regeneration was mandatory for CI and the two i18n keys are required by the project's own no-French-literal gate.

## Issues Encountered

- The development database (`letmegetin`) is behind the migrations (as 13-02 noted); every backend check here ran against `letmegetin_test` through the functional suite.
- 13-01 and 13-02 did not regenerate `docs/openapi.json`, so this plan's export carries their schema changes as well. Nothing was hand-merged; the diff is one script run.

## Known Stubs

None.

## Threat Flags

None beyond the plan's model. T-13-05 (information disclosure) is unchanged: the banner and the levels render public documentation state and React escapes every string. T-13-08 (package tampering) is moot — no package was added to either project.

## User Setup Required

None.

## Next Phase Readiness

- **The ladder is now published**: `documentation_ladder` is the only source of the bounds; anything that needs them (another client, a partner doc) reads the payload or `docs/public-api.md`, never a copy.
- **Verifier should confirm**: (a) the rendered legend, family chips and banner in a browser — no component test covers the JSX, and the 320 px wrap is still a visual backstop; (b) the empty-record path on a place with no grid (banner without link) and on one with a grid (banner with link); (c) that the two edited French literals are what the reviewers expect, since no e2e selector pins them today.
- **Not verified here**: no automated assertion of the rendered markup; the e2e suite ran against the pre-change deployment only.

---

## Self-Check: PASSED
