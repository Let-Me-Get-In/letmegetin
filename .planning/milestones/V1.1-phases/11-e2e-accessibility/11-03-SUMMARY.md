---
phase: 11-e2e-accessibility
plan: 03
subsystem: e2e
tags: [playwright, e2e, auth, contribution, review, ci, secrets]

requires:
  - plan: 11-01
    provides: "the fr/en dictionary; `contributionSaved`/`reviewPublished` are the byte-identical French the specs assert"
  - plan: 11-02
    provides: "`admin user ensure --verified`, the seeded account the authenticated specs log in as"
  - plan: 11-05
    provides: "the localized record path: `#criterion`, `#value`, `#rating`, `#body`, the completion bar and the accessibility section"
  - plan: 11-06
    provides: "the localized login page; `#email`/`#password` stay the locale-independent contract"

provides:
  - "`tests/helpers.ts`: `seededCredentials`, `skipWithoutCredentials`, `loginAsSeededUser`, `openFirstPlaceWithCriteria`"
  - "an authenticated contribution journey that only ever targets a place that actually has criteria"
  - "an authenticated review journey pinned to a single write per run"
  - "an anonymous record-detail journey (h1, accessibility section, completion bar)"
  - "`tests/auth-gate.spec.ts`: the run fails, rather than green-skips, when a required credential is missing"
  - "the CI split: credentials + `E2E_REQUIRE_AUTH` on development, `E2E_READ_ONLY` on production"

affects:
  - verify-work
  - 11-04

actuals:
  tokens: 2346
  tasks: 2
  commits: 1
  plan_head_before: e41a76179084af12f3cba94a3712cd521c22ad85
  plan_head_after: b06fc447b18172b95b91bbc385a46fe9961c815d

tech-stack:
  added: []
  patterns:
    - "A write spec guards itself with one helper call before its first navigation: production skips it, a missing credential on main/dispatch throws instead of skipping"
    - "A write spec is chromium-only (`testIgnore` on the mobile project) and opts out of retries, so a run writes exactly once"
    - "A spec that needs a populated form walks the results in list order and fails with a message naming the fixture it needs, instead of taking the first row blindly"

key-files:
  created:
    - tests/contribution.spec.ts
    - tests/review.spec.ts
    - tests/record.spec.ts
    - tests/auth-gate.spec.ts
  modified:
    - tests/helpers.ts
    - playwright.config.ts
    - .github/workflows/e2e.yaml
    - AGENTS.md

key-decisions:
  - "`skipWithoutCredentials` is the first statement of each write test body, not a describe-level call: a missing required credential then fails that test with a readable error instead of aborting the file during collection. The skip-before-any-`goto` guarantee is unchanged."
  - "`loginAsSeededUser` throws when the credentials are absent — TypeScript strict needs the narrowing anyway, and the message names the two variables."
  - "`openFirstPlaceWithCriteria` navigates by the result's `href` rather than clicking each row and going back: the list order stays deterministic and no SPA back-navigation race is introduced."
  - "The record spec scopes its `dl dt` count to the `Accessibilité` region. The completion section renders its own `dl/dt` (per-family scores), so an unscoped count would pass on every page and assert nothing."
  - "`E2E_REQUIRE_AUTH` stays empty on `pull_request` (fork PRs have no secrets, and a same-repo PR writes once against development like main does); it is `true` on push-to-main and workflow_dispatch only."
  - "The write specs keep their assertions at full strength against the old build: nothing was loosened to make an undeployed run go green."

requirements-completed: [E2E-01]

status: complete
---

# Phase 11 Plan 03: Authenticated contribution and review journeys (e2e repo) Summary

Adds the authenticated Playwright journeys — contribution and review — plus an anonymous record-detail
journey, driven by the seeded verified account, with a CI gate that fails instead of green-skipping when
the credential is missing and a bounded single-write contract.

**Code lives in the e2e repo** (`/Users/seb/Projects/letmegetin-e2e`, branch `LET-35-e2e-journeys`,
commit `b06fc44`). This summary and `STATE.md` are the only files touched in the app repo, both
uncommitted.

## What changed

| File | Change |
|---|---|
| `tests/helpers.ts` | `seededCredentials()`, `skipWithoutCredentials(t)`, `loginAsSeededUser(page)`, `openFirstPlaceWithCriteria(page, maxResults = 8)`. The four existing exports are untouched. |
| `tests/contribution.spec.ts` | Logs in through the real form, walks up to 8 results to find one whose `#criterion` has options, fills the first criterion (option select by **visible label**, boolean select, or free text), asserts `Contribution enregistrée. Merci !`. |
| `tests/review.spec.ts` | Logs in, opens the first result, posts a timestamped review at the default rating, asserts `Avis publié. Merci !`. |
| `tests/record.spec.ts` | Anonymous: opens a place detail, asserts the `h1`, the completion `role="progressbar"` with numeric `aria-valuenow`/`aria-valuemax`, and that the accessibility section renders rows **or** its explicit empty state. |
| `tests/auth-gate.spec.ts` | Always runs; when `E2E_REQUIRE_AUTH=true` it asserts both credentials exist, so a missing secret is a red run. |
| `playwright.config.ts` | `mobile` project gets `testIgnore: /(contribution|review)\.spec\.ts/` — a bare `npm test` writes each spec exactly once. |
| `.github/workflows/e2e.yaml` | Development job: `E2E_USER_EMAIL`, `E2E_USER_PASSWORD` from secrets, `E2E_REQUIRE_AUTH` empty on `pull_request` / `true` otherwise. Production job: `E2E_READ_ONLY: "true"`. |
| `AGENTS.md` | "The suite is read-only" gains the bounded exception (existing places only, timestamped marker, no delete API, development only). |

## Gates — what actually ran

```
$ cd /Users/seb/Projects/letmegetin-e2e && npx tsc --noEmit
TSC_OK
```
`npm run lint` does not exist in this repo (`package.json` has no `lint` script), so `typecheck` is the
static gate.

```
$ E2E_BASE_URL=https://app.dev.letmegetin.org npx playwright test --project=chromium
  2 skipped
  12 passed (6.6s)
```
All read-only specs pass against the **currently deployed** build, including the new `record.spec.ts`
(the pre-`LET-35` build already has the same `#criterion`/`#value` ids, `Accessibilité` heading,
`progressbar` and French success strings, so this journey is proven today). The two write specs report
**skipped** — no credentials in this shell.

Guard behaviour, verified:

```
$ E2E_REQUIRE_AUTH=true npx playwright test auth-gate.spec.ts contribution.spec.ts review.spec.ts
  3 failed   # auth-gate (missing secret) + both write specs threw from skipWithoutCredentials

$ E2E_READ_ONLY=true npx playwright test contribution.spec.ts review.spec.ts
  2 skipped  # reported skipped, no navigation

$ npx playwright test --project=mobile --list
  12 tests in 6 files   # contribution.spec.ts and review.spec.ts absent
```

## Not run — blocked on the deploy

The authenticated contribution and review runs **were not executed and are not proven**. They need
app-repo PR #33 (`LET-35-e2e-accessibility`) deployed to development plus the verified account seeded
there; neither has happened. `E2E_USER_EMAIL`/`E2E_USER_PASSWORD` are not set in this environment, so
both specs skipped rather than ran. No assertion was weakened to change that.

To close it, after PR #33 is merged and deployed:

```bash
# 1. deploy development (full 40-char sha — a short sha fails opaquely)
gh workflow run iac-deploy.yaml -R Let-Me-Get-In/letmegetin-config \
  -f environment=development -f app_sha=<40-char sha>

# 2. seed the verified account on the deployed host (password never on argv)
LETMEGETIN_USER_PASSWORD='<password>' uv run python -m letmegetin.admin \
  user ensure --verified '<email>'

# 3. run the authenticated journeys
cd /Users/seb/Projects/letmegetin-e2e && git checkout LET-35-e2e-journeys
E2E_BASE_URL=https://app.dev.letmegetin.org \
E2E_REQUIRE_AUTH=true \
E2E_USER_EMAIL='<email>' E2E_USER_PASSWORD='<password>' \
npx playwright test --project=chromium
```

## Secret wiring

- `E2E_USER_EMAIL` and `E2E_USER_PASSWORD` live as **GitHub Actions repository secrets in
  `Let-Me-Get-In/letmegetin-e2e`**, consumed only by the `development` job's Playwright step. They must
  match the account `admin user ensure --verified` minted on the deployed host.
- `LETMEGETIN_USER_PASSWORD` (plan 11-02) is an **operator shell variable**, never a repo secret and
  never on a command line. The two e2e secrets are copies of that value and the seeded email.
- Nothing enters the app runtime or the config repo's OpenTofu/Ansible values, so no config-repo
  change is needed (recorded per `docs/rules/repos.md`).

## Deviations from Plan

**1. [Rule 1 - Bug] `skipWithoutCredentials` is called inside each test body, not at describe level**
- **Found during:** Task 1
- **Issue:** a describe-level `throw` aborts collection and reports a file-level error; a test-level
  `test.skip(true, reason)` reports a clean skip. Both fail loudly, but only the test-level form gives
  the operator the spec name and the reason.
- **Fix:** call it as the first statement of the test body — still before any `goto`.
- **Files:** `tests/helpers.ts`, `tests/contribution.spec.ts`, `tests/review.spec.ts`

**2. [Rule 2 - Missing critical functionality] `loginAsSeededUser` throws on missing credentials**
- **Found during:** Task 1
- **Issue:** `fill()` needs a `string`; the credentials are optional by nature. Passing `undefined`
  would raise a confusing Playwright error far from the cause.
- **Fix:** explicit guard with a message naming both env vars.

**3. [Rule 1 - Bug] `openFirstPlaceWithCriteria` navigates by `href` instead of click-and-back**
- **Found during:** Task 1
- **Issue:** the plan's "open each result in turn" invites `goBack()`; re-settling the SPA list between
  candidates is a race the helper does not need.
- **Fix:** read each row's first link `href` and `goto` it, up to `maxResults` (default 8), then throw
  the plan's exact message.

**4. [Rule 2 - Missing critical functionality] the record spec scopes its row count to the accessibility region**
- **Found during:** Task 2
- **Issue:** the plan's "at least one `dt` row" is satisfied by the completion section, which always
  renders `dl/dt` per-family scores — the assertion would be vacuous.
- **Fix:** locate `getByRole("region", { name: /Accessibilité|Accessibility/ })` and count `dl dt`
  inside it, or accept the explicit empty-state sentence.

**5. `npm run lint` is not a gate here**
- The e2e repo has no `lint` script; `npx tsc --noEmit` is the static gate and is green.

## Threat surface

- T-11-06 (tampering by write specs): mitigated as planned — existing places only, timestamped marker,
  no create/delete, `retries: 0`, production read-only.
- T-11-07 (credential disclosure): mitigated — secrets only, never logged or committed; a fork PR has
  none and skips; `E2E_REQUIRE_AUTH` makes their absence fail on main/dispatch.
- No new threat surface beyond the plan's register (no new dependency, no new page, no new endpoint).

## Self-Check: PASSED

- `tests/contribution.spec.ts`, `tests/review.spec.ts`, `tests/record.spec.ts`, `tests/auth-gate.spec.ts`
  exist on branch `LET-35-e2e-journeys` at `b06fc44`.
- `npx tsc --noEmit` green; 12 read-only tests pass against development; write specs skip without
  credentials, fail with `E2E_REQUIRE_AUTH=true`, skip under `E2E_READ_ONLY=true`, and are absent from
  the `mobile` project.
