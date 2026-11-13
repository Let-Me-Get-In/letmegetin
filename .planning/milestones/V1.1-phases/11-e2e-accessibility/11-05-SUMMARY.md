---
phase: 11-e2e-accessibility
plan: 05
subsystem: ui
tags: [nextjs, i18n, react, accessibility, vitest]

requires:
  - plan: 11-01
    provides: "the `fr`/`en` dictionary, `t`/`tPlural`/`format`, `parseLocale`/`LOCALE_COOKIE`, and `label`/`formatValue`/`formatDate`/`familyLabel` taking a locale"

provides:
  - "the place-detail page, its 404, every `components/record/**` component and the verify banner render from the dictionary, with the locale read once per render from the cookie"
  - "locale-independent stored values: option criteria submit the option slug, booleans submit `oui`/`non`"
  - "review dates formatted in the reader's locale (`fr-FR`/`en-GB`)"

affects:
  - 11-06
  - verify-work

actuals:
  tokens: 8640
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "A server page reads the locale cookie once and threads `locale` down as a required prop; client components never read the cookie"
    - "A `<select>` whose value is persisted carries the slug (data), never the localized label (display)"

key-files:
  created: []
  modified:
    - web/src/app/places/[slug]/page.tsx
    - web/src/app/places/[slug]/not-found.tsx
    - web/src/components/record/contribution-form.tsx
    - web/src/components/record/review-form.tsx
    - web/src/components/record/review-list.tsx
    - web/src/components/record/accessibility-tree.tsx
    - web/src/components/record/photo-gallery.tsx
    - web/src/components/auth/verify-banner.tsx
    - web/src/app/account/page.tsx
    - web/src/components/record/contribution-form.test.tsx
    - web/src/components/record/review-form.test.tsx
    - web/src/components/record/accessibility-tree.test.tsx

key-decisions:
  - "The contribution option `<select>` submits `option.slug` (and booleans `oui`/`non`), so the stored accessibility value cannot depend on the display language; the e2e/API contract does not change."
  - "`VerifyBanner` now requires `locale`; the account page, still a client component, passes `DEFAULT_LOCALE` until 11-06 turns it into a server component that reads the cookie."
  - "The `#avis` fragment in the review pagination hrefs and the `/5` rating suffixes are left as literals: one is an anchor target, the other a locale-independent numeral."

patterns-established:
  - "404 segments read the locale cookie in an async `not-found.tsx`, same as the page that raises `notFound()`."

requirements-completed: [A11Y-02]

coverage:
  - id: D1
    description: "The place-detail page renders its headings, back link, rating, review-count line, completion progressbar and family scores from the dictionary, and passes `locale` to every record component and `VerifyBanner`"
    requirement: A11Y-02
    verification:
      - kind: other
        ref: "cd web && npm run typecheck && npm run build"
        status: pass
    human_judgment: true
    rationale: "The fr/en rendering itself is only asserted indirectly (unit tests cover the components); a browser check with the locale cookie set to `en` is the real proof."
  - id: D2
    description: "Contribution form stores locale-independent values: option slug for option criteria, `oui`/`non` for booleans"
    requirement: A11Y-02
    verification:
      - kind: unit
        ref: "web/src/components/record/contribution-form.test.tsx#submits the option slug, not the displayed label"
        status: pass
      - kind: unit
        ref: "web/src/components/record/contribution-form.test.tsx#sends a boolean value for a verified user"
        status: pass
    human_judgment: false
  - id: D3
    description: "The place 404 is localized with French output byte-identical to before (`Lieu introuvable` / body / `Retour à la recherche`)"
    requirement: A11Y-02
    verification:
      - kind: other
        ref: "web/src/lib/i18n.ts fr column (byte-identical literals) + cd web && npm run build"
        status: pass
    human_judgment: true
    rationale: "No test renders the route-level not-found; the French strings are asserted by the e2e suite that text-selects them, which this branch runs separately."
  - id: D4
    description: "Review dates render through `formatDate(created, locale)`"
    requirement: A11Y-02
    verification:
      - kind: unit
        ref: "web/src/lib/labels.test.ts (formatDate locale branch)"
        status: pass
    human_judgment: false
  - id: D5
    description: "`VerifyBanner` takes a required `locale`, supplied by the place page"
    requirement: A11Y-02
    verification:
      - kind: other
        ref: "cd web && npm run typecheck (required prop enforced)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-08
status: complete
---

# Phase 11 Plan 05: Record Path Localization Summary

**The place page, its 404, all `record/**` components and the verify banner render fr/en from the dictionary, and the contribution form now stores option slugs instead of French labels**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2
- **Files modified:** 12
- **Commits:** 1 (`38a2595`)

## Accomplishments

- `app/places/[slug]/page.tsx` reads the locale cookie at the top of the async component and
  renders the back link, unknown-category fallback, not-rated fallback, review-count line,
  completion heading + progressbar label, criteria percentage, Photos/Accessibility/Contribute/Reviews
  headings, contribution help and review help from `t()`/`tPlural()`/`format()`; family scores go
  through `familyLabel(family, locale)`; `locale` is passed to every record component and to
  `VerifyBanner`.
- `app/places/[slug]/not-found.tsx` is localized (async, cookie-resolved); the French output is
  byte-identical: `Lieu introuvable`, `Cette fiche n'existe pas ou a été déplacée. Essayez une
  nouvelle recherche.`, `Retour à la recherche`.
- **Correctness fix:** the contribution option `<select>` submits `option.slug` and displays
  `label(option.label, locale)` — previously the localized label *was* the value, so every stored
  option value depended on the interface language. Booleans still submit `oui`/`non`.
- **Correctness fix:** `ReviewList` formats `formatDate(review.created, locale)` (en-GB under `en`)
  and localizes the empty state, `Anonyme`, the pagination `aria-label`, Précédent/Suivant and
  `Page N / M`.
- `VerifyBanner` takes a required `locale`; `role="status"` and resend behaviour unchanged.
- Tests: the three record suites pass `locale`, plus new cases — the option submits its slug (not
  the label), the English option label and Save button, the English verify-email copy, and the
  English empty-tree state. The axe no-violations assertion still passes.

## Task Commits

One commit for the whole plan, per the repo's delivery rule (`docs/rules/delivery.md`):

1. **Tasks 1 + 2** — `38a2595` feat(i18n): localize the record path (LET-35)

## Files Modified

- `web/src/app/places/[slug]/page.tsx` — locale from the cookie, dictionary copy, locale passed down
- `web/src/app/places/[slug]/not-found.tsx` — localized 404
- `web/src/components/record/contribution-form.tsx` — `locale` prop, slug values, dictionary copy
- `web/src/components/record/review-form.tsx` — `locale` prop, dictionary copy
- `web/src/components/record/review-list.tsx` — `locale` prop, locale-aware dates and pagination
- `web/src/components/record/accessibility-tree.tsx` — `locale` prop, `label`/`formatValue` locale
- `web/src/components/record/photo-gallery.tsx` — `locale` prop, unspecified-source copy
- `web/src/components/auth/verify-banner.tsx` — required `locale`, dictionary copy
- `web/src/app/account/page.tsx` — passes `DEFAULT_LOCALE` (see deviation 1)
- `web/src/components/record/{contribution-form,review-form,accessibility-tree}.test.tsx` — `locale` prop, new en/slug cases
- `web/src/lib/i18n.ts` — **not touched**: every key this plan needed already existed

## Decisions Made

- **Slug as the submitted value**, not the label: the API stores `{"value": value}` verbatim, so a
  label would freeze the display language into the record.
- **`DEFAULT_LOCALE` on the account page** rather than a `"fr"` literal or a client-side cookie
  read: it compiles today, reads as intentional, and 11-06 replaces it with the server-resolved
  locale when it splits `account/page.tsx` into a server page + `account-view.tsx`.
- **`#avis` and `/5` stay literals**: an anchor target and a numeral, not display copy.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `account/page.tsx` had to satisfy the now-required `VerifyBanner locale`**
- **Found during:** Task 1 (`verify-banner.tsx`)
- **Issue:** The plan makes `locale` required on `VerifyBanner` and assigns the account-page call
  site to plan 11-06. `account/page.tsx` is a `"use client"` component, so it cannot read the
  cookie server-side; leaving it as `<VerifyBanner />` fails `npm run typecheck` now.
- **Fix:** the account page passes `DEFAULT_LOCALE` (imported from `@/lib/i18n`) with a one-line
  comment recording that 11-06 will supply the resolved locale. No French string literal is
  introduced, so `check:i18n` has nothing to flag.
- **Files modified:** `web/src/app/account/page.tsx`
- **Verification:** `npm run typecheck`, `npm run lint`, `npm run build` green.
- **Committed in:** `38a2595`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The account-page banner stays French-only until 11-06, which is exactly where
the plan put it. No scope creep, no new dependency.

## French literals that remain on the record path (input for the 11-06 `check:i18n` guard)

Every remaining string literal in the swept files, and why it is not display copy:

| File | Literal | Why it stays |
|------|---------|--------------|
| `components/record/contribution-form.tsx` | `value="oui"` / `value="non"`, `choice === "oui"` | Protocol values sent to the API; the visible text is `t(locale, "yes"/"no")`. |
| `components/record/contribution-form.tsx` | `value=""`, `setChoice("")`, `setText("")`, `message: ""` | Empty-state sentinels. |
| `components/record/review-list.tsx` | `` `/places/${slug}?page=…#avis` `` (2×) | Anchor target, not copy; also listed as a guard exclusion in 11-06. |
| `components/record/review-list.tsx` | `{review.rating}/5 · ` | Locale-independent numeral + separator. |
| `components/record/review-form.tsx` | `{value}/5`, `useState("5")` | Rating numerals (the `<select>` value and label). |
| `components/record/photo-gallery.tsx` | `alt=""`, `` ` · ${photo.license}` `` | Decorative image (correct for a11y) and a separator. |
| `app/places/[slug]/page.tsx` | `` ` · ${place.address}` ``, `%`, `{place.rating.toFixed(1)}/5` | Separator, percent numeral, rating numeral. |
| all files | `className`, `id`, `htmlFor`, `role`, `type`, `href`, `method`, `aria-*` values | Non-display attributes (the 11-06 guard excludes these). |
| all files | `error.message` from `ApiError` | Server-provided message, not a local literal; the fallback is `t(...)`. |

Data rendered as-is (not literals, nothing for the guard to see): `place.name`, `place.category`,
`place.address`, `photo.credit`, `photo.license`, `review.body`, `review.author_name`.

Note for 11-06: `app/layout.tsx` still holds the French `metadata.title`/`description`; the 11-06
plan already excludes the `metadata` export from the guard.

## Issues Encountered

None. `not-found.tsx` already existed as a French component (the plan said "ADD to scope"); it was
localized in place rather than created.

## Verification

- `uv run ruff check .` / `uv run ruff format --check .` / `uv run mypy` — green (no Python change).
- `cd web && npm run lint` — green.
- `cd web && npm run typecheck` — green.
- `cd web && npm test -- --run` — 8 files, 44 tests passed.
- `cd web && npm run build` — green; every route stays dynamic (`ƒ`), so the cookie read in
  `not-found.tsx` is safe.

## Next Phase Readiness

11-06 can now scan `components/record/**` and `app/places/**` for French literals and expect only
the values/attributes listed above. It still owns: the auth/account pages, the account page's
server-resolved `locale` for `VerifyBanner`, and the `check:i18n` script itself.

---
*Phase: 11-e2e-accessibility*
*Completed: 2026-11-08*

## Self-Check: PASSED

- Commit `38a2595` is an ancestor of HEAD.
- All 6 spot-checked artifacts exist (12 files changed in the commit).
