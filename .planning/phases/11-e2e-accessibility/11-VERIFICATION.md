---
phase: 11-e2e-accessibility
verified: 2026-11-11T20:14:36Z
status: human_needed
score: 13/14 must-haves verified
covered_files:
  - .planning/phases/11-e2e-accessibility/11-01-PLAN.md
  - .planning/phases/11-e2e-accessibility/11-01-SUMMARY.md
  - .planning/phases/11-e2e-accessibility/11-02-PLAN.md
  - .planning/phases/11-e2e-accessibility/11-02-SUMMARY.md
  - .planning/phases/11-e2e-accessibility/11-03-PLAN.md
  - .planning/phases/11-e2e-accessibility/11-03-SUMMARY.md
  - .planning/phases/11-e2e-accessibility/11-04-PLAN.md
  - .planning/phases/11-e2e-accessibility/11-04-SUMMARY.md
  - .planning/phases/11-e2e-accessibility/11-05-PLAN.md
  - .planning/phases/11-e2e-accessibility/11-05-SUMMARY.md
  - .planning/phases/11-e2e-accessibility/11-06-PLAN.md
  - .planning/phases/11-e2e-accessibility/11-06-SUMMARY.md
  - .planning/phases/11-e2e-accessibility/11-07-PLAN.md
  - .planning/phases/11-e2e-accessibility/11-07-SUMMARY.md
  - src/letmegetin/admin.py
  - src/letmegetin/application/accounts/register.py
  - src/letmegetin/application/accounts/users.py
  - tests/functional/accounts/test_user_command.py
  - tests/unit/application/accounts/test_ensure_user.py
  - web/package.json
  - web/scripts/check-i18n.mjs
  - web/src/app/(auth)/login/page.tsx
  - web/src/app/(auth)/register/page.tsx
  - web/src/app/(auth)/verify/page.tsx
  - web/src/app/account/page.tsx
  - web/src/app/globals.css
  - web/src/app/layout.tsx
  - web/src/app/page.tsx
  - web/src/app/places/[slug]/not-found.tsx
  - web/src/app/places/[slug]/page.tsx
  - web/src/components/account/account-view.tsx
  - web/src/components/auth/login-form.tsx
  - web/src/components/auth/register-form.tsx
  - web/src/components/auth/require-auth.tsx
  - web/src/components/auth/verify-banner.tsx
  - web/src/components/auth/verify-email.tsx
  - web/src/components/record/accessibility-tree.tsx
  - web/src/components/record/contribution-form.tsx
  - web/src/components/record/photo-gallery.tsx
  - web/src/components/record/review-form.tsx
  - web/src/components/record/review-list.tsx
  - web/src/components/search/filters.tsx
  - web/src/components/search/map-view.tsx
  - web/src/components/search/place-list.tsx
  - web/src/components/search/search-view.tsx
  - web/src/lib/i18n.test.ts
  - web/src/lib/i18n.ts
  - web/src/lib/labels.test.ts
  - web/src/lib/labels.ts
  - web/src/lib/search.test.ts
  - web/src/lib/search.ts
covered_digest: "v4:sha256:0e5458bc589d4888a5de18bf21c4fc9296d3e0de1fe24b5600881f716fa9ec33"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run the 12-row VoiceOver (macOS/Safari) + NVDA (Windows/Chromium) protocol in `letmegetin-e2e/docs/screen-reader-audit.md` over search and record, in both fr and en, and record the results in `docs/screen-reader-audit-template.md`."
    expected: "Every row has a VoiceOver and an NVDA result, the severity legend is applied (`blocker | major | minor`), and any blocker/major names its fix. Until then the template reads 'No rows recorded yet — human pass pending'."
    why_human: "Screen-reader announcements (heading navigation, live-region timing, focus order, map non-focusability in practice) cannot be observed by this verifier; no tool in this repo executes VoiceOver or NVDA. The machine half (strict axe) is green and the protocol is written, but the pass itself has not been performed."
    owner: "LET-82"
---

# Phase 11: E2E & Accessibility Verification Report

**Phase Goal:** Prove the user journey in a browser and with assistive technology.
**Verified:** 2026-11-11T20:14:36Z
**Status:** human_needed
**Re-verification:** No — initial verification

> **Mode note (MVP).** `ROADMAP.md` marks this phase `Mode: mvp`, but the goal is not a user story; `query user-story.validate` rejects it (missing "As a …, I want to …, so that …"). Rather than refuse verification of an already-executed, UAT-complete phase, this report verifies the four roadmap success criteria and adds a User Flow Coverage table derived from the 14-row UAT.

## Goal Achievement

### User Flow Coverage (MVP mode)

| # | Journey step | Expected | Evidence in codebase | Status |
|---|--------------|----------|----------------------|--------|
| 1 | Search renders in the reader's language | fr or en copy, localized map label | `app/page.tsx` reads the `locale` cookie → `SearchView` → `Filters`/`PlaceList`/`MapView`; `lib/i18n.ts` dictionary; `lib/search.ts` `FAMILY_KEYS` | ✓ VERIFIED (UAT 1, 2) |
| 2 | Open a place record | Localized detail page, completion bar, accessibility tree, contribution + review forms | `app/places/[slug]/page.tsx` reads the cookie, passes `locale` to every record component; re-tested after LET-83 (`b2c073b`) | ✓ VERIFIED (UAT 3) |
| 3 | Authenticate | Login/register/verify localized, persisted language | `app/(auth)/*/page.tsx` are async cookie readers; `LoginForm`/`RegisterForm`/`VerifyEmail` take `locale` | ✓ VERIFIED (UAT 4) |
| 4 | Account page | Localized account + verify banner in the current language | `app/account/page.tsx` (server) → `AccountView` → `RequireAuth`/`VerifyBanner` | ✓ VERIFIED (UAT 5) |
| 5 | Contribute to a record | Success message in the current language, value persisted, no language-dependent value | `contribution-form.tsx` submits the option **slug** / `oui`\`non`; e2e `contribution.spec.ts` drives the real form | ✓ VERIFIED (UAT 6) |
| 6 | Publish a review | Review appears, date formatted in the current locale, no duplicate | `review-list.tsx` `formatDate(review.created, locale)`; e2e `review.spec.ts` with `retries: 0` | ✓ VERIFIED (UAT 7) |
| 7 | Assistive navigation | Machine-checkable a11y gate green + human screen-reader pass | strict axe scan over search + record passes (`seriousCriticalCount: 0`); map contract + keyboard list pass; **human pass outstanding** | ⚠️ MACHINE VERIFIED, HUMAN NEEDED (LET-82) |

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A Playwright suite in a separate repo covers search, record, contribution and review in CI (E2E-01 / SC1) | ✓ VERIFIED | `letmegetin-e2e/tests/{search,places,account,accessibility}/**` — `npx playwright test --list` = 30 tests in 9 files; `.github/workflows/e2e.yaml` runs chromium against development on push/PR |
| 2 | The contribution spec logs in as the seeded verified account through the real form and posts to a place that has criteria (E2E-01) | ✓ VERIFIED | `tests/account/contribution.spec.ts` uses `loginAsSeededUser` (`#email`/`#password`) and `openFirstPlaceWithCriteria`; UAT test 6 passed in the browser |
| 3 | The review spec posts a review and the record spec asserts the accessibility section (E2E-01) | ✓ VERIFIED | `tests/account/review.spec.ts` (`#body`, asserts `Avis publié. Merci !`); `tests/places/record.spec.ts` (`h1`, progressbar aria values, accessibility region rows or empty state); UAT 7 and 3 passed |
| 4 | CI honesty: fork PRs skip, push/dispatch fails on a missing secret, production is read-only, write specs do not retry (E2E-01) | ✓ VERIFIED | `tests/support/helpers.ts#skipWithoutCredentials`; `tests/account/auth-gate.spec.ts`; `playwright.config.ts` mobile `testIgnore` + spec-level `retries: 0`; workflow sets `E2E_REQUIRE_AUTH` (`!= pull_request`), `E2E_READ_ONLY` on production |
| 5 | `admin user ensure --verified` is idempotent, fails loudly on a password mismatch, never takes the password on argv, and writes through `UserRepository` (E2E-01) | ✓ VERIFIED | `application/accounts/users.py#ensure_user`; `admin.py#user_app` + `_run_user_admin`; `uv run pytest tests/unit/application/accounts/test_ensure_user.py` = 11 passed; functional = 3 passed; no `--password` option |
| 6 | `t()` accepts string keys only; plural words come from `tPlural`; French counts 0 as singular; dates/values follow the locale (A11Y-02) | ✓ VERIFIED | `lib/i18n.ts` `StringMessageKey`/`PluralKey` derivation + `tPlural` (`count === 1 \|\| (locale === "fr" && count === 0)`); `lib/labels.ts` `formatDate` en-GB/fr-FR; `npm test -- --run` = 58 tests passed |
| 7 | The locale cookie is read once per server render on search, record, auth and account, and `<html lang>` follows it (A11Y-02) | ✓ VERIFIED | `app/layout.tsx:58-65`, `app/page.tsx`, `app/places/[slug]/page.tsx:60`, `app/(auth)/*/page.tsx`, `app/account/page.tsx`; UAT 1, 2, 4, 5 |
| 8 | The record path renders fr/en; persisted values are locale-independent (option slug, `oui`/`non`); review dates use `formatDate(created, locale)`; `#avis` stays an anchor (A11Y-02) | ✓ VERIFIED | `contribution-form.tsx:109,131,151-152` (`value={item.slug}` / `option.slug`, `oui`/`non`); `review-list.tsx:35`; UAT 3 re-tested after LET-83 |
| 9 | The account page resolves the locale on the server and passes it to `AccountView`, which passes it to `VerifyBanner` (A11Y-02) | ✓ VERIFIED | `app/account/page.tsx` (async, cookie) → `account-view.tsx:10,14,21`; `VerifyBanner` takes a required `locale` |
| 10 | `check:i18n` scans literals in JSX text, expression literals and call arguments, excludes non-display attributes/test files/`metadata`/`t()` keys, and is enforced by lint (A11Y-02) | ✓ VERIFIED | `web/scripts/check-i18n.mjs` (AST walk, `EXCLUDED_ATTRS`, `DENYLIST`); `package.json` `lint = eslint . && node scripts/check-i18n.mjs`; ran it: `30 files scanned, no French literal`, exit 0; failure proof recorded in 11-06-SUMMARY |
| 11 | The map is `role="application"`, non-focusable, and its localized aria-label points at the list as the keyboard path (A11Y-03) | ✓ VERIFIED | `map-view.tsx` (`role="application"`, `aria-label={t(locale, "mapAriaLabel")}`, no `tabindex`); `accessibility.spec.ts` asserts `/list/i` and refuses `tabindex="0"`; ran against dev — 3/3 passed |
| 12 | All serious/critical axe findings are fixed and the development CI job enforces `AXE_STRICT=1` (A11Y-01 machine half) | ✓ VERIFIED | `globals.css` underlines `.maplibregl-ctrl-attrib a:link/:visited`; `.github/workflows/e2e.yaml:55` `AXE_STRICT: "1"`; local strict run over dev passed 2/2 and wrote `seriousCriticalCount: 0` |
| 13 | The screen-reader audit is documented: protocol, expected announcements, severity legend and an explicit "outstanding" statement, plus a blank results sheet (A11Y-01 documented half) | ✓ VERIFIED | `docs/screen-reader-audit.md` (S1–S6, R1–R6, legend, Status section); `docs/screen-reader-audit-template.md` ("No rows recorded yet — human pass pending") |
| 14 | The human VoiceOver/NVDA pass was performed and recorded (A11Y-01, SC2 "screen-reader audit") | ? NEEDS HUMAN (LET-82) | The results sheet is blank; the phase's own docs and STATE.md say the pass is outstanding. UAT row 9 records "pass", but that is not the 12-row protocol (VoiceOver + NVDA, both locales) and no rows were recorded. |

**Score:** 13/14 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `web/src/lib/i18n.ts` | fr/en dictionary, typed `t`/`tPlural`/`format` | ✓ VERIFIED | exists, consumed across all pages; 58 web tests |
| `web/src/lib/labels.ts` | locale-aware `label`/`formatValue`/`formatDate` | ✓ VERIFIED | en-GB / fr-FR dates |
| `web/src/lib/search.ts` | ordered `FAMILY_KEYS` + `familyLabel` | ✓ VERIFIED | used by `filters.tsx` and the record page |
| `web/src/app/page.tsx` | server cookie read → `SearchView` | ✓ VERIFIED | WIRED |
| `web/src/app/places/[slug]/page.tsx` | cookie locale → all record components | ✓ VERIFIED | WIRED |
| `web/src/app/places/[slug]/not-found.tsx` | localized 404 | ✓ VERIFIED | async cookie read |
| `web/src/components/account/account-view.tsx` | localized account body receiving `locale` | ✓ VERIFIED | WIRED to `RequireAuth` + `VerifyBanner` |
| `web/src/components/auth/verify-banner.tsx` | required `locale` | ✓ VERIFIED | both render sites pass it |
| `web/scripts/check-i18n.mjs` | AST French-literal guard | ✓ VERIFIED | wired into `npm run lint`; runs green |
| `web/src/app/globals.css` | MapLibre attribution underline | ✓ VERIFIED | rule present; strict scan green |
| `src/letmegetin/application/accounts/users.py` | `ensure_user` use case | ✓ VERIFIED | 11 unit tests pass |
| `src/letmegetin/admin.py` | `user ensure` sub-command | ✓ VERIFIED | commit-only runner; no `--password` |
| e2e `tests/support/axe.ts` + `tests/accessibility/a11y.spec.ts` | WCAG A/AA scans writing an artifact | ✓ VERIFIED | ran strict against dev; artifact `{scanned, seriousCriticalCount: 0, violations: []}` |
| e2e `tests/account/{contribution,review,auth-gate}.spec.ts` | authenticated + guard journeys | ✓ VERIFIED | present and enumerated by Playwright; write specs skip without credentials by design |
| e2e `tests/places/record.spec.ts`, `tests/search/**` | record + search/filter/pagination journeys | ✓ VERIFIED | present; record spec passed in the strict accessibility run |
| e2e `docs/screen-reader-audit.md` + template | protocol + blank results sheet | ✓ VERIFIED | template is intentionally blank |
| e2e `tests/accessibility/accessibility.spec.ts` | map contract + keyboard list | ✓ VERIFIED | ran against dev — 3/3 passed |
| `.github/workflows/e2e.yaml` | strict axe dev job, read-only prod job | ✓ VERIFIED | `AXE_STRICT: "1"` (development); `E2E_READ_ONLY: "true"` (production) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/page.tsx` | `SearchView` → filters/list/map | `locale` prop threaded | WIRED | grep + component signatures |
| `app/places/[slug]/page.tsx` | record components + `VerifyBanner` | `locale` prop on each | WIRED | `ContributionForm tree={…} locale={locale}` etc. |
| `app/account/page.tsx` | `AccountView` → `VerifyBanner` | server-resolved `locale` | WIRED | `account-view.tsx:14,21` |
| `admin user ensure` | `ensure_user` → `UserRepository` | `_run_user_admin` (commit-only) | WIRED | no `_run_admin` grid rebuild |
| e2e `contribution.spec.ts` | real login form → authenticated write | `loginAsSeededUser` (`#email`/`#password`) | WIRED | helpers + spec |
| e2e `a11y.spec.ts` | `test-results/axe-violations.json` → CI artifact | `record()` write | WIRED | artifact observed non-empty, `seriousCriticalCount: 0` |
| development CI job | strict gate | `AXE_STRICT=1` env | WIRED | parsed in workflow |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| pages / components | `locale` | `cookies().get(LOCALE_COOKIE)` on each server page | Yes — real request cookie | ✓ FLOWING |
| rendered copy | `t(locale, key)` / `tPlural` | `MESSAGES` dictionary in `lib/i18n.ts` | Yes — static dictionary, not a mock | ✓ FLOWING |
| record page | `place`, `reviews` | API fetch (server/components) | Yes | ✓ FLOWING |
| axe artifact | `violations` | `@axe-core/playwright` scan of the live page | Yes — 2 pages scanned | ✓ FLOWING |
| `admin user ensure` | user row | `UserRepository.add` / `mark_email_verified` | Yes — DB write (functional test) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| i18n guard passes on the tree | `cd web && npm run check:i18n` | `30 files scanned, no French literal`, exit 0 | ✓ PASS |
| web typecheck + unit suite | `cd web && npm run typecheck && npm test -- --run` | clean; 10 files, 58 tests passed | ✓ PASS |
| `ensure_user` use case | `uv run pytest tests/unit/application/accounts/test_ensure_user.py -q` | 11 passed | ✓ PASS |
| `user ensure` CLI contract | `uv run pytest tests/functional/accounts/test_user_command.py -q` | 3 passed | ✓ PASS |
| strict axe + accessibility specs vs dev | `E2E_BASE_URL=https://app.dev.letmegetin.org AXE_STRICT=1 npx playwright test accessibility/ --project=chromium` | 5 passed; artifact `seriousCriticalCount: 0` | ✓ PASS |
| e2e suite enumerates all journeys | `npx playwright test --list` | 30 tests in 9 files (contribution/review chromium-only) | ✓ PASS |
| full chromium suite vs dev | `E2E_BASE_URL=… npx playwright test --project=chromium` | 8 passed, 2 skipped (no creds), 6 failed with `alert: Rate limit exceeded` on the page snapshot | ⚠️ ENVIRONMENTAL — the documented dev rate-limit item; the same specs pass when run first after a cooldown and passed in the phase's recorded gate run. Not a code regression. |

### Probe Execution

N/A — no `scripts/*/tests/probe-*.sh` and no probe declared by this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| E2E-01 | 11-02, 11-03 | A browser e2e suite in a separate repo covers search, record, contribution and review | ✓ SATISFIED | specs enumerated + CI workflow + seeded-account CLI (tests pass); UAT 3/6/7 prove the journeys in a browser |
| A11Y-01 | 11-04, 11-07 | A screen-reader audit of search and record is documented with fixes | ⚠️ PARTIAL — human pass outstanding | strict axe gate green (`seriousCriticalCount: 0`) and protocol/template exist; the VoiceOver/NVDA pass is not performed (blank sheet), owner **LET-82** |
| A11Y-02 | 11-01, 11-05, 11-06 | The UI ships fr/en strings with a persisted language | ✓ SATISFIED | dictionary + cookie plumbing + record/auth/account sweep; `check:i18n` green; UAT 1–5 |
| A11Y-03 | 11-01, 11-04 | The map has a usable non-visual path (list + keyboard) | ✓ SATISFIED (automated contract) | `map-view.tsx` non-focusable + localized label pointing at the list; `accessibility.spec.ts` 3/3 passed against dev; human-audit validation folds into LET-82 |

No orphaned requirements: every ID declared across plans and mapped in REQUIREMENTS.md (E2E-01, A11Y-01, A11Y-02, A11Y-03) appears above.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `letmegetin-e2e/README.md` | 54-56 | Says the axe scan is "report-only … until `AXE_STRICT=1` is turned on in CI" — it is now on | ℹ️ Info | Documentation drift; the authoritative workflow sets `AXE_STRICT: "1"` and the audit doc says it is enforced |
| `letmegetin-e2e/tests/accessibility/a11y.spec.ts` | 8-14 | `shortcut:` comment says "the hard gate … stays off in this repo" — stale | ℹ️ Info | Same drift; no functional effect |
| phase-modified files | — | No `TBD` / `FIXME` / `XXX` markers | — | Debt-marker gate clear |
| app + e2e | — | No stub returns / hardcoded empty data flow on the audited paths | — | — |

### Human Verification Required

#### 1. Screen-reader pass (VoiceOver + NVDA) — owner LET-82

**Test:** Follow `letmegetin-e2e/docs/screen-reader-audit.md` with VoiceOver (macOS/Safari) and NVDA (Windows/Chromium). Walk the search journey (S1–S6) and the record journey (R1–R6), in both `fr` and `en`. Record each result in `docs/screen-reader-audit-template.md`, apply the `blocker | major | minor` legend, and link a fix for every blocker/major.
**Expected:** All 12 rows filled for both screen readers; map is not a focus stop and its label points at the list; result-count and "Voir plus" changes are announced; completion bar and accessibility tree announce their values; form submits are announced.
**Why human:** Screen-reader announcements, live-region timing and focus order cannot be observed by this verifier and no tool here runs VoiceOver/NVDA. The protocol and machine gate exist; the pass does not. The blank results sheet ("No rows recorded yet — human pass pending") is the observable evidence that it has not been done.

### Gaps Summary

No code gap blocks the phase. The machine-checkable side of the goal is achieved and independently re-run during this verification: the strict axe scan reports zero serious/critical, the map non-visual contract and keyboard list pass, the fr/en dictionary is complete and guarded, the record/auth/account paths read the cookie server-side, the seeded-account CLI is idempotent and tested, and the e2e repo contains and enumerates search, record, contribution, review and axe specs with an honest CI gate.

Two things must be stated rather than glossed:

1. **A11Y-01's human half is not done.** `11-UAT.md` row 9 says "pass", but the phase's own results sheet is blank and the protocol requires 12 recorded rows across two screen readers and two locales. The repo's convention (ROADMAP "Complete (screen-reader pass outstanding)", STATE.md, `deferred-items.md`) is that the pass is outstanding. This report therefore records **human_needed**, owner **LET-82**, and does not mark A11Y-01 fully complete.
2. **The full e2e run can trip the app's own rate limit.** Repeated full runs produced 6 failures whose snapshots read `Rate limit exceeded` / `0 lieu`; this is the documented `deferred-items.md` issue (60 rpm/IP against a suite that makes many calls), not a regression. The isolated strict axe + accessibility run is green, and the phase's recorded gate run was 14 passed / 2 skipped.

Note on commit hashes: the SUMMARY files cite pre-rebase SHAs that are no longer ancestors of `HEAD`; the same work is present in the history as `6342ace`, `992d0c1`, `be23bc7`, `1661bee`, `4a2c7b8` (app) and `b06fc44`/`580b133`/`20f67ad` (e2e, preserved as objects). Verification was performed against the working tree and history, not the cited strings.

Also: `REQUIREMENTS.md` still lists E2E-01/A11Y-01/A11Y-02/A11Y-03 as `Pending`; that table is updated at phase closure, so it is not counted as a gap here.

---

_Verified: 2026-11-11T20:14:36Z_
_Verifier: the agent (gsd-verifier)_
