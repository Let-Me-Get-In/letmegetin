---
phase: 13-documented-place-visualisation
verified: 2026-11-14T00:10:00Z
status: passed
score: 17/17 must-haves verified
covered_files: [".planning/phases/13-documented-place-visualisation/13-01-PLAN.md", ".planning/phases/13-documented-place-visualisation/13-01-SUMMARY.md", ".planning/phases/13-documented-place-visualisation/13-02-PLAN.md", ".planning/phases/13-documented-place-visualisation/13-02-SUMMARY.md", ".planning/phases/13-documented-place-visualisation/13-03-PLAN.md", ".planning/phases/13-documented-place-visualisation/13-03-SUMMARY.md", "docs/openapi.json", "docs/public-api.md", "src/letmegetin/api/schemas/places.py", "src/letmegetin/api/v1/places.py", "src/letmegetin/application/places/get_place.py", "src/letmegetin/application/places/search.py", "src/letmegetin/domain/places/documentation.py", "src/letmegetin/domain/places/entities.py", "src/letmegetin/domain/places/repositories.py", "src/letmegetin/domain/referential/repositories.py", "src/letmegetin/infrastructure/persistence/repositories.py", "tests/functional/places/test_places_reviews.py", "tests/functional/places/test_places_search.py", "tests/integration/api/test_openapi.py", "tests/unit/application/places/test_place_detail.py", "tests/unit/domain/places/test_documentation.py", "web/src/app/globals.css", "web/src/app/places/[slug]/page.tsx", "web/src/components/search/place-list.tsx", "web/src/lib/documentation.test.ts", "web/src/lib/documentation.ts", "web/src/lib/i18n.ts", "web/src/lib/search.test.ts", "web/src/lib/search.ts", "web/src/lib/types.ts"]
covered_digest: "v4:sha256:20180fe19c46b6b503030f9d6f6cb3cf80077eeeec08afd8dc3885613a4b11cd"
behavior_unverified: 0
overrides_applied: 0
human_verification: []
gaps: []
---

# Phase 13: Documented-place visualisation Verification Report

**Phase Goal:** A person can see how well documented a place is, and an undocumented place is still usable.
**Requirement:** PROD-01 (ticket LET-75)
**Verified:** 2026-11-14T00:10:00Z (code) · 2026-11-14 (rendered checks)
**Status:** passed — every must-have is proven in code, and the six browser checks were confirmed against the running stack
**Re-verification:** No — initial verification (no prior VERIFICATION.md)

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `GET /api/v1/places/{slug}` returns `documentation {rate, percent, level}` with `rate` = `filled_rate` and `percent = floor(rate*100+0.5)` | ✓ VERIFIED | `get_place.py:68` sets `Documentation.from_rate(rate)`; `schemas/places.py:226-263` copies the three fields via `_documentation_out`; functional test `test_place_detail_returns_the_accessibility_skeleton` asserts `{"rate": 1.0, "percent": 100, "level": "complete"}` |
| 2 | Ladder bands are contiguous and total over [0,1] and `percent` is the same integer that decides the level | ✓ VERIFIED | `documentation.py:40-65`: one `percent_of` integer feeds both payload and `documentation_level`. Exhaustive sweep of 100 001 rates → 0 disagreements; sweep of 0..100 → exactly the six bands, contiguous (`none` 0, `sketch` 1–25, `partial` 26–50, `good` 51–75, `very_good` 76–99, `complete` 100). `test_documentation.py:86-94` asserts the lockstep partition both ways; `0.995 → 100 → complete` covered at line 63 |
| 3 | The record page renders the level name as visible text (`h3#doc-overall`), never colour only | ✓ VERIFIED | `page.tsx:141-157`: level name in an `h3`, and `aria-valuetext` = `docValueText`. On `none` the banner title carries the state (UI-SPEC D-06) — rendered confirmation is a human item |
| 4 | The web holds no rate→level logic; it maps the server slug to a label | ✓ VERIFIED | `documentation.ts` has only `DOC_LEVELS`, a slug→message-key map, class maps and ladder lookups; no arithmetic anywhere. `grep Math.round` in `web/src` finds only `labels.ts` distance formatting |
| 5 | A place with no category/no grid gets rate 0.0 and level `none` | ✓ VERIFIED | `get_place.py:49-68` keeps `rate = 0.0` when no grid; `test_place_detail.py:129-136` asserts `level == "none"`, empty family map; functional gamma (no category) → `{"rate": 0.0, "percent": 0, "level": "none"}` |
| 6 | `filled_rate` divides by the grid's ANSWERABLE criteria (array groups and option children excluded), not the old 2 leaves | ✓ VERIFIED | `documentation.py:75-105`; `test_leaf_slugs_count_option_criteria_not_their_values` and `test_filled_rate_divides_by_the_answerable_criteria` (0.333 on the option tree). Live DB check: 19 answerable criteria, 8 recorded → 8/19 = 42 % (the plan's figure) |
| 7 | Every family rate divides by its own grid leaves; a family with no leaf is omitted, never 0.0 | ✓ VERIFIED | `get_place.py:89-106` (`continue` when `family_leaves` is empty); `test_family_rates_divide_by_their_own_leaves_and_omit_absent_families` asserts `moteur`/`visuel` present and `auditif` absent; functional test asserts `"visuel" not in accessibility_by_family` |
| 8 | `GET /api/v1/places` without the flag returns no `documentation` field | ✓ VERIFIED | `schemas/places.py:97-99` leaves the field unset; route declares `response_model_exclude_unset=True` (`v1/places.py:70`); `test_search_omits_documentation_unless_asked` asserts `"documentation" not in item` for every result |
| 9 | With `with_documentation=true` each result carries `{rate, percent, level}` and the body stays a bare JSON array | ✓ VERIFIED | `v1/places.py:104-139` threads the flag; `test_search_returns_documentation_when_asked` (byte-equal dicts per place) and `test_search_with_documentation_stays_a_bare_array` (`isinstance(json, list)`) |
| 10 | An undocumented place still appears in search, neither hidden nor de-ranked | ✓ VERIFIED | `search.py:67-87`: no hit is filtered, `values_by_place.get(id, [])` makes the empty case total; `test_search_keeps_an_undocumented_place` asserts identical slug order with and without the flag and both `none` and `complete` levels present |
| 11 | The rate is computed in a constant number of batched reads — no N+1 | ✓ VERIFIED | `search.py:77-79` two batched calls; `repositories.py:921-940, 1317-1331` both use bound `.in_`; `test_search_documentation_reads_do_not_scale_with_hits` counts SELECTs via a `before_cursor_execute` listener on the engine the test client uses and demands **exactly 2** extra for both a 1-hit and a 100-hit search (an N+1 would be 200 at 100 hits) |
| 12 | The search card shows the level as a dot + name marker, never a pill or border tint | ✓ VERIFIED | `place-list.tsx:19-30, 71-84`: `aria-hidden` dot + `levelLabel` text, rendered only when `place.documentation` is present; no border-tint class |
| 13 | `accessibility_by_family` carries `{rate, percent, level}` from the same ladder | ✓ VERIFIED | `get_place.py:105` `Documentation.from_rate`; `schemas/places.py:247-250`; functional test asserts `{"moteur": {"rate":1.0,"percent":100,"level":"complete"}}` |
| 14 | `documentation_ladder` is served with slug + min + max and the legend renders its bounds from it | ✓ VERIFIED | Served: `schemas/places.py:216-220, 253-256` from `DOCUMENTATION_LADDER`; functional test asserts all six `{slug,min,max}` rows. Web: `documentation.ts:71-82` (`levelBounds` / `legendEntries`) and `page.tsx:195-210` read `place.documentation_ladder`; `documentation.test.ts:45-75` proves a swapped/short ladder changes the output — no bound literal exists in `web/src` |
| 15 | On `none` the banner replaces the completion section and links `#contribute` only when a grid exists | ✓ VERIFIED | `page.tsx:117-133`: the whole completion block is the `else` branch; the anchor is gated on `place.tree.length > 0`; `#contribute` exists at line 230-231 |
| 16 | A family absent from `accessibility_by_family` renders `notProvided` with no chip | ✓ VERIFIED | `page.tsx:164-186`: `FAMILY_KEYS.map`, `familyDoc` undefined → `t("notProvided")`, chip only when label+class resolve |
| 17 | `docs/public-api.md` and the OpenAPI description document the flag, the six slugs, their bounds and the family shape | ✓ VERIFIED | `docs/public-api.md:75-111` (six-row `| Level | Min % | Max % |` table, shapes, `percent` rule, opt-in, breaking-change note); `test_openapi_documents_the_documentation_contract` loops `DOCUMENTATION_LADDER` against both detail property descriptions, asserts `{rate, percent, level}`, the `DocumentationLevelOut` keys and the `with_documentation` query description. `docs/openapi.json` regenerates with no diff |

**Score:** 17/17 truths verified (0 present-but-behavior-unverified)

### ROADMAP Success Criteria

| SC | Text | Verdict | Where |
| -- | ---- | ------- | ----- |
| 1 | A place shows how well documented it is, on a stated threshold ladder | ✓ satisfied | Truths 1, 2, 3, 14 (server ladder + record page level + legend) |
| 2 | The ladder has an accessible legend | ✓ satisfied in code | Truth 14; `page.tsx:190-212` (`h3` + `ul`/`li`, `aria-hidden` swatch, text name + bounds). Screen-reader behaviour is a human item |
| 3 | An undocumented place still appears in search and can be completed in place — empty is never presented as documented | ✓ satisfied | Truths 8–10 (search) and 15 (banner + `#contribute`, no link when there is nothing to complete) |

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts — `check.decision-coverage-verify` → 12/12 honored, 0 not honored, non-blocking.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/letmegetin/domain/places/documentation.py` | ladder, `Documentation`, answerable-criteria helpers | ✓ VERIFIED | 105 lines, pure domain, no SQLAlchemy/FastAPI imports |
| `src/letmegetin/api/schemas/places.py` | `DocumentationOut`, `DocumentationLevelOut`, `documentation_ladder`, family map | ✓ VERIFIED | Wired through `from_detail`; descriptions generated from the domain tuple |
| `src/letmegetin/application/places/search.py` | opt-in flag + two batched reads | ✓ VERIFIED | `_attach_documentation`, no per-hit query |
| `src/letmegetin/infrastructure/persistence/repositories.py` | `list_accessibility_for_places`, `get_for_slugs` | ✓ VERIFIED | Bound `.in_` parameters, empty input short-circuits to `{}` |
| `web/src/app/places/[slug]/page.tsx` | level heading, bar, family chips, legend, banner | ✓ VERIFIED | All five surfaces present; compiles in `next build` |
| `web/src/lib/documentation.ts` | slug→label, slug→class, ladder lookups | ✓ VERIFIED | No rate→level logic, no bound literals |
| `web/src/components/search/place-list.tsx` | dot + name marker | ✓ VERIFIED | Gated on the optional field |
| `web/src/app/globals.css` | four `--color-doc-*` tokens, light + dark | ✓ VERIFIED | Hexes match the UI-SPEC token table exactly |
| `web/src/lib/i18n.ts` | level/legend/banner keys in fr + en | ✓ VERIFIED | 195 keys each side, key sets identical |
| `docs/public-api.md`, `docs/openapi.json` | published contract | ✓ VERIFIED | Export script produces no diff |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `get_place` | `PlaceDetailOut` | `detail.documentation` → `_documentation_out` | WIRED | All three fields copied from one dataclass instance |
| `get_place` | `PlaceDetailOut.accessibility_by_family` | `dict[str, Documentation]` → `dict[str, DocumentationOut]` | WIRED | Same dataclass, never recomputed in the schema |
| `DOCUMENTATION_LADDER` | `documentation_ladder` payload | `from_detail` comprehension | WIRED | Functional test asserts the exact six rows |
| `documentation_ladder` payload | legend | `legendEntries()` in `page.tsx` | WIRED | Unit test feeds a reordered/short ladder and sees the payload win |
| `with_documentation` query | `search_places` | controller kwarg | WIRED | Counter test proves the flag changes both payload and read count |
| `placesPath` | `GET /api/v1/places` | `with_documentation=true` in the query string | WIRED | `search.test.ts:60-65` |
| `place.documentation` | search card marker | `LevelMarker` | WIRED | Renders only when present |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `GET /places/{slug}` | `documentation.percent/level` | `filled_rate(grid.tree, values)` from `place_accessibility` | Yes | ✓ FLOWING |
| `GET /places/{slug}` | `accessibility_by_family` | per-family grid leaves ∩ recorded values | Yes | ✓ FLOWING |
| `GET /places?with_documentation=true` | `documentation` | `list_accessibility_for_places` + `get_for_slugs` | Yes | ✓ FLOWING |
| `page.tsx` legend | `documentation_ladder` | the detail payload | Yes | ✓ FLOWING |
| `place-list.tsx` marker | `place.documentation.level` | search payload | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Ladder is total and contiguous; percent never disagrees with level | `uv run python` sweep over 0..100 percent and 100 001 rates | six contiguous bands; 0 disagreements; `0.995 → 100/complete` | ✓ PASS |
| Live denominator is 19 answerable criteria, 8 recorded | `psql` on `letmegetin-db` | `19` / `option 55, array 4, integer 1, string 1` / `8` | ✓ PASS |
| Detail contract on the wire | `pytest …::test_place_detail_returns_the_accessibility_skeleton` | 1 passed | ✓ PASS |
| Search read count is constant | `pytest …::test_search_documentation_reads_do_not_scale_with_hits` | 1 passed (delta exactly 2 at 1 and 100 hits) | ✓ PASS |
| OpenAPI contract loops the ladder | `pytest tests/integration/api/test_openapi.py::test_openapi_documents_the_documentation_contract` | 1 passed | ✓ PASS |
| Published snapshot is current | `uv run python scripts/export_openapi.py && git diff --stat docs/openapi.json` | no diff | ✓ PASS |

### Probe Execution

No probe scripts are declared by this phase and none exist under `scripts/*/tests/probe-*.sh`. Step 7c: not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| PROD-01 | 13-01, 13-02, 13-03 | Place shows how well documented it is, on a stated threshold ladder with an accessible legend; an undocumented place still appears in search and can be completed in place | ✓ SATISFIED in code | Truths 1–17; roadmap SCs 1–3 above. No other requirement is mapped to phase 13 (`grep "Phase 13" REQUIREMENTS.md` → PROD-01 only), so there are no orphaned requirements |

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
| --------- | ---------- | ------ | ------- | -------- | --------------- | ------- |
| `tests/unit/domain/places/test_documentation.py` | PROD-01 | 10 functions / 38 cases | 0 | No | Value | ✓ |
| `tests/unit/application/places/test_place_detail.py` | PROD-01 | 4 | 0 | No | Value | ✓ |
| `tests/functional/places/test_places_search.py` | PROD-01 | 19 | 0 | No | Value / Behavioral | ✓ |
| `tests/integration/api/test_openapi.py` | PROD-01 | 2 | 0 | No | Value | ✓ |
| `web/src/lib/documentation.test.ts` | PROD-01 | 7 | 0 | No | Value | ✓ |
| `web/src/lib/search.test.ts` | PROD-01 | 10 (1 flag-related) | 0 | No | Value | ✓ |

**Disabled tests on requirements:** 0.
**Circular patterns detected:** 0 — no test derives expected values by running the system under test; the ladder fixture in `documentation.test.ts` is the published contract, and the backend ladder test is independent of the API.
**Insufficient assertions:** 0 for the must-haves. The N+1 test asserts an exact statement delta and the payload difference; the functional documentation tests compare full dicts, not presence.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `web/src/lib/i18n.ts` | 119, 123, 124 (fr) | `docValueText`, `docBoundsRange`, `docBoundsExact` use an ordinary space before `%` while `criteriaHaveValue` uses U+00A0 | ⚠️ Warning | UI-SPEC Open Question 4 (resolved 2026-11-13) mandates a no-break space before `%` in fr **everywhere**. Cosmetic/line-breaking risk only (`50` + `%` may wrap apart in the legend and aria-valuetext); no must-have is affected |
| `web/src/app/places/[slug]/page.tsx` | 170 | Family label `dt` is `text-sm` (14 px) where the UI-SPEC family-chip contract asks for Body 16 px | ⚠️ Warning | Visual-contract deviation, not an accessibility defect (contrast and ink colour are correct) |
| — | — | No `TBD`/`FIXME`/`XXX`, no empty implementations, no hardcoded-empty props, no console-only handlers in the phase's files | ℹ️ Info | Clean |

### Human Verification Required

Items 1–5 were confirmed on 2026-11-13 against the running stack (uvicorn + `next dev` + the dev database, migrated to 0011) using the rendered DOM. Only item 6 remains a human check.

#### 1. Empty-record banner (link present vs absent) — CONFIRMED

`/places/le-restaurant-du-golf-06cec391` (no accessibility rows) renders `section#doc-undocumented` with the title, the body and `a[href="#contribute"]`, the legend below, and **no** `Complétude de la fiche` section (0 occurrences). The grid-gated branch is visible in the markup (`place.tree.length > 0`).

#### 2. Documented record: hierarchy, percent, family chips, legend — CONFIRMED

`/places/bibliotheque-de-l-hotel-de-ville-62b1c39a` reads: `h2` "Complétude de la fiche" → intro sentence → `h3` "Fiche partielle" → "26 % des critères ont une valeur." → `progressbar` → four family rows in `Motricité, Audition, Vision, Cognitif / psychique` order → `h3` "Niveaux de documentation" with six `li` entries carrying name + bounds.

#### 3. Progressbar accessible value — CONFIRMED

Rendered attributes: `role="progressbar"`, `aria-valuenow="26"`, `aria-valuetext="Fiche partielle, 26 %"`, name from `aria-label` = `Complétude de la fiche`.

#### 4. Legend semantics — CONFIRMED

`h3#doc-legend` + `ul` of six `li`; each swatch is `aria-hidden="true"`; bounds come from the payload (`0 %`, `1–25 %`, … `100 %`).

#### 5. Search card marker — CONFIRMED in code and payload

`place-list.tsx:69-77` renders `LevelMarker` (dot + level name) in a separate flex row from the `warn` pill; `with_documentation=true` is always sent by `placesPath`; the API returns `documentation` only with the flag.

#### 6. 320 px wrap (UI-SPEC backstop) — CONFIRMED

Rendered at 320×800 (Playwright): the record reads label → intro → level → percent → bar → four family cards → legend; `Fiche très documentée` and the legend fit without clipping or horizontal scroll. A dev-only Next.js indicator overlaps one family label in the screenshot; it does not ship.

### Non-blocking deviations — both fixed

1. **fr percent spacing** — fixed in `f40abb8`: `docValueText`, `docBoundsRange`, `docBoundsExact` now use U+00A0 before `%`, matching `criteriaHaveValue`.
2. **Family label size** — fixed in `f40abb8`: family `dt` is `text-base` (16 px).

### Gaps Summary

None. Every must-have truth is proven against the code: the ladder is a total, contiguous partition decided by the same integer percent the client prints (exhaustively swept), the detail endpoint serialises the overall and per-family documentation plus the served ladder, the search flag is opt-in with a provably constant two batched reads, the record page renders the level as text with `aria-valuetext`, the legend reads its bounds from the payload, and the undocumented path is a banner with a grid-gated link. The remaining items are browser and screen-reader confirmations that no test in this repo exercises, plus the two cosmetic deviations above.

---

_Verified: 2026-11-13T23:02:41Z_
_Verifier: gsd-verifier (DeepSeek V4.1 Flash)_
