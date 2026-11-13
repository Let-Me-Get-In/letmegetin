---
phase: 11-e2e-accessibility
plan: 04
subsystem: e2e
tags: [playwright, e2e, axe, accessibility, i18n, docs]

requires:
  - plan: 11-01
    provides: "the localized map aria-label (`mapAriaLabel` in both locales) that A11Y-03's assertion now accepts"
  - plan: 11-03
    provides: "`openSearch`/`resultCount` and the read-only spec conventions the axe scan reuses"
  - plan: 11-05
    provides: "the record page (h1, accessibility region, completion bar) the second axe scan covers"

provides:
  - "`tests/axe.ts` — `axeScan(page)`, the WCAG A/AA tag set and `color-contrast` disable the app's unit gate already uses"
  - "`tests/a11y.spec.ts` — report-only axe scans of search + record writing `test-results/axe-violations.json`"
  - "the axe inventory itself: one serious violation, `link-in-text-block`, the MapLibre attribution link on the search page"
  - "`docs/screen-reader-audit.md` — the human audit protocol, journey steps, severity legend and outstanding statement"
  - "`docs/screen-reader-audit-template.md` — the blank results sheet the human fills"
  - "the localized map assertion: `/list/i` accepts both locales, `tabindex=\"0\"` still refused"

affects:
  - 11-07
  - verify-work

actuals:
  tokens: 4300
  tasks: 3
  commits: 1
  plan_head_before: b06fc447b18172b95b91bbc385a46fe9961c815d
  plan_head_after: 580b133

tech-stack:
  added:
    - "@axe-core/playwright 4.14.0 (devDependency, official Deque package, verified on npm and by same-vendor precedent with the app's `axe-core ^4.14.0`)"
  patterns:
    - "The report artifact is written by read-modify-write per page: a page's rows are replaced, so a rerun cannot double-count and a worker restarted after a failure cannot erase the other page's findings"
    - "One artifact file per Playwright project, because chromium and mobile are separate workers and a shared file would let the slower scan overwrite the other's rows"
    - "A scan waits for the last client-only thing to hydrate (the map) before running: a half-rendered page reports zero violations, which is a false negative a follow-up fix plan would trust"

key-files:
  created:
    - tests/axe.ts
    - tests/a11y.spec.ts
    - docs/screen-reader-audit.md
    - docs/screen-reader-audit-template.md
  modified:
    - tests/accessibility.spec.ts
    - README.md
    - package.json
    - package-lock.json

key-decisions:
  - "The axe gate is **report-only** (`AXE_STRICT` unset): every serious/critical finding lives in the app repo, which this repo's commit cannot touch, so the fixes and the strict flip are plan 11-07's — fed by this plan's artifact."
  - "`test-results/axe-violations.json` carries `{ baseUrl, scanned, seriousCriticalCount, violations }`, and each violation gains a `page` field, because 11-07 must know which page a target belongs to."
  - "The scan is skipped by nothing and gated by nothing on `moderate`/`minor`: those rows feed the audit template but never block, which keeps the report honest without a red suite for taste."
  - "The search scan waits for `role=\"application\"` before running axe. Under parallel load the map hydrates late; scanning early recorded zero violations once, and an artifact with a quiet zero is worse than no artifact."
  - "`accessibility.spec.ts` asserts `/list/i`, not `/liste/i`: the label is localized (11-01), and a case-insensitive `list` is a substring of both `liste` and `list` — one assertion, two locales, no locale switch in the test."
  - "`tabindex=\"0\"` is still refused. Localizing the label did not change what the map is for: it is not a keyboard destination, the list is."

requirements-completed: [A11Y-03]

status: complete
---

# Phase 11 Plan 04: Report-only axe scan, screen-reader audit protocol and localized map contract Summary

Wires axe-core into the e2e suite over the search and record pages as a **report-only** scan that
writes a machine-consumable inventory, writes the human screen-reader audit protocol plus its blank
results sheet, and moves the map assertion onto the localized label — A11Y-01 as far as an agent can
take it, A11Y-03 closed on the verification side.

**Code lives in the e2e repo** (`/Users/seb/Projects/letmegetin-e2e`, branch `LET-35-e2e-journeys`,
commit `580b133`). This summary, `STATE.md` and `deferred-items.md` are the only files touched in the
app repo, all uncommitted (the phase's `.planning` docs commit is the orchestrator's, per the
one-docs-commit-per-phase rule).

## The axe inventory — the input of plan 11-07

Produced by an actual run against `https://app.dev.letmegetin.org` (app `1661bee`), identical on the
`chromium` and `mobile` projects across repeated runs:

| Page | Rule | Impact | Nodes | Target | Why it fires |
|---|---|---|---|---|---|
| search | `link-in-text-block` | **serious** | 1 | `a[href$="maplibre.org/"]` | the MapLibre attribution link has 2.02:1 contrast against its surrounding text and no underline — WCAG 1.4.1 |
| record | — | — | 0 | — | no violations under the A/AA tag set |

`seriousCriticalCount: 1`. No `critical`, no `moderate`, no `minor` rows in this run.

The single finding is in the map library's attribution control, not in the app's own markup: 11-07
fixes it in `web/` with a CSS override on the attribution link (underline or a darker text colour),
not by rewriting a component. Verified that the gate has teeth: `AXE_STRICT=1` fails both scans with
`Received: 1`, and reports zero-finding pages green.

## What changed

| File | Change |
|---|---|
| `package.json` / `package-lock.json` | `@axe-core/playwright@^4.14.0` devDependency. Official Deque (`github.com/dequelabs/axe-core-npm`), same vendor as the app's pinned `axe-core ^4.14.0`. |
| `tests/axe.ts` | `axeScan(page)` = `AxeBuilder.withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa"]).disableRules(["color-contrast"]).analyze()` — byte-identical policy to `web/src/components/record/accessibility-tree.test.tsx`. |
| `tests/a11y.spec.ts` | Two scans (search after `openSearch` + the map visible; record after the first result's h1). Writes `test-results/axe-violations.json`, asserts the artifact is non-empty and well-formed, and asserts `seriousCriticalCount === 0` **only** under `AXE_STRICT=1`. |
| `tests/accessibility.spec.ts` | One line in the third test: `/liste/i` → `/list/i`. The two other tests untouched. |
| `docs/screen-reader-audit.md` | Scope (search + record), toolchain (VoiceOver/Safari, NVDA/Chromium), expected announcements (landmarks, headings, live regions, non-focusable map), the 12-step pass/fail grid with the required header row, the `blocker \| major \| minor` legend, and the explicit outstanding statement. |
| `docs/screen-reader-audit-template.md` | The blank sheet: same header row, same legend, `No rows recorded yet — human pass pending`. |
| `README.md` | "What it covers" rows for `record`, `contribution`, `review` and `a11y`; a new "Accessibility audit" section linking both docs and stating the scan is report-only and the human pass outstanding. |

## Gates — what actually ran

```
$ cd /Users/seb/Projects/letmegetin-e2e && npx tsc --noEmit
TYPECHECK_OK

$ E2E_BASE_URL=https://app.dev.letmegetin.org npx playwright test --project=chromium
  2 skipped
  14 passed (7.2s)
```
The two skips are `contribution.spec.ts` and `review.spec.ts` — no `E2E_USER_EMAIL`/`E2E_USER_PASSWORD`
in this shell, by design. Every other spec passes against the deployed dev build, `a11y.spec.ts`
included. `a11y.spec.ts` also passes on the `mobile` project and writes
`test-results/axe-violations-mobile.json` with the same single finding.

```
$ AXE_STRICT=1 ... npx playwright test a11y.spec.ts --project=chromium
  2 failed    # Received: 1 — the strict gate would block today, which is the point
```

## Deviations from Plan

**1. [Rule 1 - Bug] the search scan waits for the map before running axe**
- **Found during:** the full-suite gate run
- **Issue:** under five parallel workers the client-only map (`dynamic(..., { ssr: false })`) had not
  hydrated when the scan ran. axe scanned a page without the map and recorded **zero** violations —
  the artifact said "all clear" while the MapLibre attribution defect was present. A follow-up fix plan
  reading that file would have fixed nothing.
- **Fix:** `await expect(page.getByRole("application")).toBeVisible()` before `axeScan`. Three
  standalone repeats and three full-suite runs then reported the same single violation.
- **Files:** `tests/a11y.spec.ts`

**2. [Rule 2 - Missing critical functionality] one artifact file per project, and per-page replacement instead of append**
- **Found during:** Task 1
- **Issue:** chromium and mobile run in separate workers against one path; the slower scan's
  read-modify-write could drop the other's rows, and Playwright restarts a worker after a failure, so a
  `beforeAll` reset would wipe the first page's findings on exactly the runs that matter.
- **Fix:** `axe-violations.json` for chromium, `axe-violations-<project>.json` otherwise; `record()`
  replaces a page's rows and recomputes `seriousCriticalCount` from what remains, so a rerun is
  idempotent and a worker restart is harmless.
- **Files:** `tests/a11y.spec.ts`

**3. [Rule 1 - Bug] the `shortcut:` comment names no GSD plan id**
- The plan's comment text names plan 11-07; the repo's message rules keep plan ids out of committed
  text, so the comment says "the follow-up app-repo plan" and the SUMMARY records the number. Same
  information for a reader who needs it, no workflow vocabulary in the source.

**4. Out of scope, recorded in `deferred-items.md`: a full local run can trip the app's own rate limit**
- The suite makes more than 60 `/api/v1/*` calls per rolling minute from one IP (each search page load
  fetches 100 places plus categories, and Next.js prefetches visible place routes). The deployed API's
  `rate_limit_default_rpm` is 60, so back-to-back full runs intermittently render "Aucun lieu trouvé"
  with `alert: Rate limit exceeded` — three unrelated pre-existing specs failed that way during this
  plan's gate attempts, and the same command is fully green after a ~70 s cooldown. Not caused by, and
  not fixable in, this plan: it is either a higher dev limit, fewer prefetches, or `retries` in CI.
- Every gate run above was a **first run after a cooldown**, so no green is a rate-limit accident.

## A11Y-01 status — deliberately not claimed

A11Y-01 has two halves and this plan delivers one and a half:

- the **automated** half: the scan runs, records, and the strict gate and its app-repo fixes are
  explicitly deferred to plan **11-07**, which consumes `test-results/axe-violations.json`;
- the **documented** half: the protocol and the blank template exist, with the required columns, the
  severity legend and the outstanding statement.

The **human VoiceOver/NVDA pass itself is not performed**. A11Y-01 therefore stays open; only A11Y-03
is marked complete by this plan. Nothing in the docs or the README claims the pass happened.

## Threat surface

- T-11-08 (axe output as information disclosure): accepted as planned — rule ids, selectors and element
  summaries only, no user data; `test-results/` is git-ignored and uploaded as an artifact.
- T-11-09 (DoS by scanning a live page): accepted — two extra page loads, no new endpoint, no writes.
- T-11-SC (package install): mitigated — `@axe-core/playwright@4.14.0` verified on npm
  (`repository: github.com/dequelabs/axe-core-npm`) before install, same vendor and version line as the
  app's `axe-core`.
- No new surface beyond the plan's register.

## Self-Check: PASSED

- `tests/axe.ts`, `tests/a11y.spec.ts`, `docs/screen-reader-audit.md`,
  `docs/screen-reader-audit-template.md` exist at commit `580b133` on `LET-35-e2e-journeys`.
- `npx tsc --noEmit` green; 14 tests pass and 2 skip (write specs, no credentials) against development.
- The artifact exists, is non-empty and well-formed, and carries `seriousCriticalCount: 1` with the
  single `link-in-text-block` finding; `AXE_STRICT=1` fails on it, as intended.
- The audit docs pass the plan's structure assertion (header row, legend, outstanding statement).
