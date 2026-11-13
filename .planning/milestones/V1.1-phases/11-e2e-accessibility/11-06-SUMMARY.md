---
phase: 11-e2e-accessibility
plan: 06
subsystem: ui
tags: [nextjs, i18n, react, accessibility, guard, ast]

requires:
  - plan: 11-01
    provides: "the fr/en dictionary, `t`/`tPlural`/`format`, `parseLocale`/`LOCALE_COOKIE`, and the auth/account keys"
  - plan: 11-05
    provides: "the record path localized, and `VerifyBanner` taking a required `locale`"

provides:
  - "login, register, verify-email and the account page render fr/en from the dictionary, with the locale read once from the cookie on the server"
  - "`web/src/components/account/account-view.tsx`: the account body as a client view receiving the server-resolved `locale`, which closes the second `VerifyBanner` render site"
  - "`npm run check:i18n`: an AST guard that fails on French literals in JSX text, JSX-expression literals and call arguments across the swept tree"
  - "`npm run lint` now runs the guard, so the existing CI `web` job enforces it with no workflow change"

affects:
  - 11-03
  - 11-04
  - 11-07
  - verify-work

actuals:
  tokens: 6595
  tasks: 3
  commits: 1
  plan_head_before: 38a2595
  plan_head_after: f041d04

tech-stack:
  added: []
  patterns:
    - "A page that needs the locale is an async server component that reads the cookie and renders a client view with `locale` as a required prop"
    - "Interface-copy regression guard: walk the TypeScript AST and flag French literals in any position, excluding non-display attributes, test files and the `metadata` export"

key-files:
  created:
    - web/scripts/check-i18n.mjs
    - web/src/components/account/account-view.tsx
  modified:
    - web/package.json
    - web/src/app/(auth)/login/page.tsx
    - web/src/app/(auth)/register/page.tsx
    - web/src/app/(auth)/verify/page.tsx
    - web/src/app/account/page.tsx
    - web/src/components/auth/login-form.tsx
    - web/src/components/auth/register-form.tsx
    - web/src/components/auth/require-auth.tsx
    - web/src/components/auth/verify-email.tsx

key-decisions:
  - "`aria-labelledby` joins the guard's non-display attribute exclusions: it holds element ids (`aria-labelledby=\"avis\"`), exactly like `id`. Without it the guard flagged two id references on the place page. `aria-label` stays scanned, because it is copy."
  - "The guard also skips the key argument of `t()`/`tPlural()`: it is a dictionary identifier, not display copy. Without that, the key `\"photos\"` matched the `Photos` denylist token and the guard could never pass."
  - "The guard is chained into `npm run lint` (`eslint . && node scripts/check-i18n.mjs`) rather than added as its own CI step: the existing `web` job already runs `npm run lint`, so CI enforces it with no `ci.yml` edit."
  - "`account/page.tsx` is now a thin async server component; every string and the `RequireAuth` wrapper moved to `account-view.tsx`, so no client component reads the cookie."

patterns-established:
  - "The `DEFAULT_LOCALE` placeholder left on `account/page.tsx` by 11-05 is gone; both `VerifyBanner` render sites now receive a server-resolved locale."

requirements-completed: [A11Y-02]

coverage:
  - id: D1
    description: "Login, register and verify pages render their heading, intro and Suspense fallback from the dictionary, with the locale read from the cookie"
    requirement: A11Y-02
    verification:
      - kind: other
        ref: "cd web && npm run typecheck && npm run build"
        status: pass
    human_judgment: true
    rationale: "No unit test renders these routes; the fr/en output is proven by setting the cookie and loading the page in a browser or in the e2e suite."
  - id: D2
    description: "The account page passes a server-resolved locale to `AccountView`, which passes it to `VerifyBanner`"
    requirement: A11Y-02
    verification:
      - kind: other
        ref: "cd web && npm run typecheck (required `locale` prop on `VerifyBanner`) && npm run build (/account stays dynamic)"
        status: pass
    human_judgment: false
  - id: D3
    description: "`check:i18n` exits 0 on the swept tree, exits 1 when the real `{place.category ?? \"Catégorie inconnue\"}` shape is reintroduced, and does not flag a plain-string `href=\"#avis\"`"
    requirement: A11Y-02
    verification:
      - kind: other
        ref: "npm run check:i18n (three proofs transcribed below)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-11-08
status: complete
---

# Phase 11 Plan 06: Auth/Account Localization and the `check:i18n` Guard Summary

**The last French-only surfaces — login, register, verify-email and the account page — now render fr/en from the dictionary, and `check:i18n` walks the AST to fail the build on any French literal reintroduced in the swept tree, wired into `npm run lint` so CI enforces it for free**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3
- **Files changed:** 11 (337 insertions, 108 deletions)
- **Commits:** 1 (`f041d04`)

## Accomplishments

- `app/(auth)/login|register|verify/page.tsx` are async server components that read the
  `locale` cookie once and render the heading, intro and Suspense fallback from `t()`; the
  static `metadata` exports are untouched (SEO title, not interface chrome).
- `LoginForm`, `RegisterForm`, `VerifyEmail` and `RequireAuth` take `locale: Locale` and render
  every label, hint, placeholder, pending label, error fallback and link from the dictionary.
  The `#email` / `#password` ids and the submit behaviour are unchanged.
- `app/account/page.tsx` is now a thin server component rendering `<AccountView locale={locale} />`;
  `components/account/account-view.tsx` holds the moved body, wraps it in
  `<RequireAuth locale={locale}>` and passes `locale` to `<VerifyBanner>`, closing the second
  render site 11-05 had to stub with `DEFAULT_LOCALE`.
- `scripts/check-i18n.mjs` (214 lines, `typescript` compiler API only — no new dependency) builds
  a 24-file list from the six swept dirs plus five single files, collects **every** string literal
  (`ts.isStringLiteral` / `ts.isNoSubstitutionTemplateLiteral`) in any position, and flags a literal
  carrying an accented French character or a denylist token. Exclusions: `href`, `className`, `id`,
  `key`, `value`, `type`, `role`, `name`, `htmlFor`, `aria-labelledby`, `data-*`, `*.test.*` /
  `*.spec.*`, the `metadata`/`generateMetadata` declarations, and `t()`/`tPlural()` key arguments.
  A missing scan root throws instead of silently shrinking coverage.
- `package.json`: `"check:i18n": "node scripts/check-i18n.mjs"`, and `"lint"` is now
  `"eslint . && node scripts/check-i18n.mjs"`. `.github/workflows/ci.yml` was **not** edited —
  its `web` job already runs `npm run lint`.

## Guard proofs (verbatim)

**(a) PASS on the produced tree**

```
$ npm run check:i18n
> letmegetin-web@1.0.0 check:i18n
> node scripts/check-i18n.mjs

check:i18n: 24 files scanned, no French literal.
EXIT=0
```

**(b) FAIL when the real expression shape is reintroduced**
`web/src/components/search/place-list.tsx:51` was temporarily changed from
`{place.category ?? t(locale, "unknownCategory")}` back to the exact shape that existed before
plan 11-01 — `{place.category ?? "Catégorie inconnue"}` — then reverted:

```
$ grep -n 'Catégorie inconnue' src/components/search/place-list.tsx
51:              {place.category ?? "Catégorie inconnue"}
$ node scripts/check-i18n.mjs
src/components/search/place-list.tsx:51  "Catégorie inconnue"
check:i18n: 1 French literal(s) in 24 scanned file(s). Move them to src/lib/i18n.ts and render them with t().
EXIT=1
$ git checkout -- src/components/search/place-list.tsx   # reverted
```

This proves the guard reads literals in JSX **expression** positions, not just JSX text nodes.

**(c) FALSE-POSITIVE control: `#avis` in an `href` does not trip it**
The real `#avis` in `review-list.tsx` sits in a template-literal `href`, which the guard never
collects. To prove the `href` exclusion itself, line 45 was temporarily reduced to a plain string
literal — the shape the denylist token `avis` *would* catch if `href` were scanned — then reverted:

```
$ grep -n 'href="#avis"' src/components/record/review-list.tsx
45:            <Link className="underline" href="#avis">
$ node scripts/check-i18n.mjs
check:i18n: 24 files scanned, no French literal.
EXIT=0
$ git checkout -- src/components/record/review-list.tsx   # reverted
```

## Task Commits

One commit for the whole plan, per `docs/rules/delivery.md`:

1. **Tasks 1 + 2 + 3** — `f041d04` feat(i18n): localize auth and account pages, add check:i18n (LET-35)

## Files Modified

- `web/src/app/(auth)/login/page.tsx` — async, cookie locale, dictionary copy, `locale` to `LoginForm`
- `web/src/app/(auth)/register/page.tsx` — same, `locale` to `RegisterForm`
- `web/src/app/(auth)/verify/page.tsx` — same, `locale` to `VerifyEmail`
- `web/src/components/auth/login-form.tsx` — `locale` prop, all copy through `t()`
- `web/src/components/auth/register-form.tsx` — `locale` prop, placeholder via `t()`
- `web/src/components/auth/verify-email.tsx` — `locale` prop, status messages through `t()`, `locale` in the effect deps
- `web/src/components/auth/require-auth.tsx` — `locale` prop, loading/redirecting messages
- `web/src/app/account/page.tsx` — reduced to an async server component reading the cookie
- `web/src/components/account/account-view.tsx` — **new**, the localized client body, `RequireAuth` + `VerifyBanner` receive `locale`
- `web/scripts/check-i18n.mjs` — **new**, the guard
- `web/package.json` — `check:i18n` script; `lint` now chains it
- `web/src/lib/i18n.ts` — **not touched**: every key this plan needed was already declared by 11-01

## Decisions Made

- **`aria-labelledby` excluded** from the guard: it references element ids (`aria-labelledby="avis"`),
  exactly like `id`. `aria-label` stays scanned because it is copy.
- **`t()`/`tPlural()` key arguments excluded**: the key is an identifier, not copy. Without this,
  `t(locale, "photos")` matched the `Photos` denylist token and the guard could never pass.
- **Guard chained into `npm run lint`** instead of a new CI step: the existing `web` job already
  runs lint, so CI coverage costs nothing and `ci.yml` is untouched.
- **Server page + client view**, not a client-side cookie read: one source of truth, no hydration
  mismatch, matching the pattern 11-01/11-05 established for the search and record paths.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Guard's attribute exclusions needed `aria-labelledby`**
- **Found during:** Task 3 (first guard run)
- **Issue:** `app/places/[slug]/page.tsx` uses `aria-labelledby="photos"` and `aria-labelledby="avis"`.
  Both are id references; the plain denylist heuristics (`Photos`, `avis`) flagged them, so the guard
  exited 1 on the tree it was supposed to bless.
- **Fix:** added `aria-labelledby` to the non-display attribute set, with a comment saying
  `aria-label` remains scanned because it is copy.
- **Files modified:** `web/scripts/check-i18n.mjs`
- **Verification:** `npm run check:i18n` → 24 files scanned, no French literal, exit 0.
- **Committed in:** `f041d04`

**2. [Rule 2 - Missing critical functionality] Guard would have failed on `t()` keys**
- **Found during:** Task 3 (same run, after fix 1)
- **Issue:** `t(locale, "photos")` is a string literal in a call argument, so it is collected; the
  denylist token `Photos` matches it case-insensitively, so no tree could ever pass.
- **Fix:** the ancestor walk returns "not display copy" when the literal is argument 1 of a call to
  `t`/`tPlural`. Reachable via nested expressions too (the walk tracks the direct child of the call).
- **Files modified:** `web/scripts/check-i18n.mjs`
- **Verification:** proof (a) above; proof (b) still fails as expected.
- **Committed in:** `f041d04`

### Plan gap, filled as the plan directed

The plan names a fallback key for the verify page (`verifying`) but not for the login page, whose
Suspense fallback was `Chargement…`. Used the existing `t(locale, "loading")` — whose fr value is
byte-identical to `Chargement…` — rather than adding a key.

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical guard rule)
**Impact on plan:** Both were necessary for the guard to pass on a correct tree; neither adds a
dependency, widens scope, or changes any rendered French string.

## Handoff for the e2e plans (11-03/11-04/11-07)

An authenticated journey sees these on `/login` with the `locale` cookie at `en`
(`<html lang="en">` comes from `layout.tsx`):

| Element | Selector | Visible English text |
|---|---|---|
| Page heading | `h1` / `getByRole("heading", { level: 1 })` | `Sign in` |
| Intro | `section > p` | `Sign in to contribute to a record or leave a review.` |
| Email label + input | `label[for="email"]`, `input#email` | `Email` |
| Password label + input | `label[for="password"]`, `input#password` | `Password` |
| Submit | `getByRole("button", { name: "Sign in" })` | `Sign in` → `Signing in…` while pending |
| Error | `p[role="alert"]` | server message, else `Could not sign in.` |
| Register link | `a[href="/register"]` | `Create an account` |
| Suspense fallback | `p[role="status"]`-less `<p>` | `Loading…` |

Because `Sign in` appears three times on `/login` (header nav link, `h1`, submit button), select the
submit by **role=button**, never by text alone. Prefer `#email` / `#password` — those ids are
contractual and unchanged.

After a successful login the redirect target is `/account` (or the `?next=` path). With `en`, that
page reads: `h1` `My account`, intro `Your contributions and reviews are published under your display
name.`, `dt` labels `Email` / `Display name` / `Email verified` / `Role`, values `Anonymous` when no
display name, `Yes` / `No` for verification, link `Search for a place`, button `Sign out`; while
the session loads, `Loading account…`; an unverified account also shows the banner
`Your email address is not verified yet: contribution and reviews are disabled.` with button
`Resend the link`.

Under the default `fr` cookie the French text is byte-identical to before this plan
(`Connexion`, `Se connecter`, `Mot de passe`, `Mon compte`, `Se déconnecter`, …), so the existing
French text selectors keep working.

## Known Stubs

None. No placeholder, empty data source or skipped assertion was introduced.

## Threat Flags

None. The guard reads a fixed set of local source files at lint time; no new network surface, no new
dependency (`typescript` was already a dev dependency), and the `locale` cookie keeps going through
`parseLocale`, which collapses unknown values to `fr`.

## Issues Encountered

`npm run build` was not affected by the new server/client split: all routes stay dynamic (`ƒ`),
including `/account`, which is what makes the cookie read safe. Pre-commit's `git stash` cycle
touched no files: the commit touched only `web/**`, so every Python hook skipped.

## Verification

- `cd /Users/seb/Projects/letmegetin && uv run ruff check .` — `All checks passed!`
- `uv run ruff format --check .` — `216 files already formatted`
- `uv run mypy` — `Success: no issues found in 75 source files`
- `cd web && npm run lint` — eslint clean, then `check:i18n: 24 files scanned, no French literal.`
- `cd web && npm run typecheck` — clean
- `cd web && npm test -- --run` — 8 files, 44 tests passed
- `cd web && npm run check:i18n` — exit 0, 24 files
- `cd web && npm run build` — compiled; `/`, `/account`, `/login`, `/places/[slug]`, `/register`,
  `/verify` all `ƒ` (dynamic)

---
*Phase: 11-e2e-accessibility*
*Completed: 2026-11-08*

## Self-Check: PASSED

- Commit `f041d04` is an ancestor of HEAD (`git merge-base --is-ancestor`).
- `web/scripts/check-i18n.mjs` and `web/src/components/account/account-view.tsx` exist and are tracked.
- `npm run check:i18n` exits 0 on the committed tree.
