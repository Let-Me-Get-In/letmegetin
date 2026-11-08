---
phase: 11-e2e-accessibility
plan: 01
subsystem: web
tags: [i18n, nextjs, accessibility, search, cookies]
requires:
  - phase: 10.1-search-pagination
    provides: "`SearchView` with a paged results list and the `placesPath(state, offset)` helper"
provides:
  - "`lib/i18n.ts` as the single owner of every interface message: search, record and auth/account keys declared once"
  - "`t(locale, key)` typed to string keys only; `tPlural(locale, key, count)` (fr treats 0 as singular); `format(message, vars)` for `{name}`"
  - "`StringMessageKey` / `PluralKey` types"
  - "`HomePage` reads the `locale` cookie server-side and passes `locale` into `SearchView`"
  - "`label(value, locale)` / `formatValue(value, locale)` / `formatDate(iso, locale)` locale-aware (fr-FR vs en-GB)"
  - "`FAMILY_KEYS` (ordered moteur, auditif, visuel, mental) + `familyLabel(family, locale)` replacing the French-only `FAMILY_LABELS`"
  - "the whole search path renders from `t()`/`tPlural()` in fr and en, including the map aria-label"
affects: [11-05, 11-06]

actuals:
  tokens: 7046
  tasks: 2
  commits: 1
  plan_head_before: aa7923b15b61e8c07b628079524dc96bef4c00fb
  plan_head_after: 819c389dac8e7c92bae25b0009ec1219dd35bbc9

tech-stack:
  added: []
  patterns:
    - "A plural key is an object `{one, many}` in every locale, and `t` is derived to accept string-valued keys only, so `t(locale, \"places\")` is a compile error and a plural word can only come from `tPlural`. The type guard is the enforcement; no runtime check."
    - "Zero is singular in French (`0 lieu`), plural in English (`0 places`): the rule lives in `tPlural`, so no call site re-implements a `count > 1` test."
    - "The locale cookie is read once per server render (`layout.tsx` for `<html lang>`, `page.tsx` for the page tree) and passed down as a prop. Client components never read the cookie, so there is one source of truth and no hydration mismatch."
    - "`formatValue` threads `locale` explicitly through its array branch (`value.map((item) => …)`) because `value.map(formatValue)` would pass the array index as the second argument."

key-files:
  created: []
  modified:
    - web/src/lib/i18n.ts
    - web/src/lib/i18n.test.ts
    - web/src/lib/labels.ts
    - web/src/lib/labels.test.ts
    - web/src/lib/search.ts
    - web/src/lib/search.test.ts
    - web/src/app/page.tsx
    - web/src/app/places/[slug]/page.tsx
    - web/src/components/search/search-view.tsx
    - web/src/components/search/filters.tsx
    - web/src/components/search/place-list.tsx
    - web/src/components/search/map-view.tsx

key-decisions:
  - "The dictionary is declared once, in this plan, including the record and auth/account keys that 11-05 and 11-06 will render: those plans consume keys, they never add any. Over-declaring a key is cheap; a missing key at 11-05 time is a cross-plan edit."
  - "The `fr` column is the reference and stays byte-identical to the literals it replaced, because the e2e suite in `letmegetin-e2e` text-selects them (`/^\\d+ lieux?$/`, \"Voir plus\", \"supplémentaire\")."
  - "`familyLabel(family, locale = \"fr\")` keeps a default locale, like `label`/`formatValue`/`formatDate`: the record page still renders French until 11-05 sweeps it, and the default documents that rather than hardcoding `\"fr\"` at the call site."
  - "`places` moved from a scalar to a plural object. It was consumed nowhere, so the change breaks no caller — verified by grep before editing."

requirements-completed: [A11Y-02, A11Y-03]

coverage:
  - id: D1
    description: "`t()` is string-key-only, so `t(locale, \"places\")` is a compile error; plural keys are reachable only through `tPlural`."
    requirement: A11Y-02
    verification:
      - kind: build
        ref: "web: npm run typecheck"
        status: pass
      - kind: unit
        ref: "web/src/lib/i18n.test.ts#pluralises in the reader's language"
        status: pass
  - id: D2
    description: "French treats 0 as singular (`0 lieu`), English does not (`0 places`); 1 and 4 pluralise per locale."
    requirement: A11Y-02
    verification:
      - kind: unit
        ref: "web/src/lib/i18n.test.ts#treats zero as singular in French only"
        status: pass
      - kind: unit
        ref: "web/src/lib/i18n.test.ts#pluralises in the reader's language"
        status: pass
  - id: D3
    description: "`{name}` placeholders resolve through `format` (page numbers, review counts, percentages)."
    requirement: A11Y-02
    verification:
      - kind: unit
        ref: "web/src/lib/i18n.test.ts#resolves {name} placeholders"
        status: pass
  - id: D4
    description: "The search page renders from the cookie-resolved locale: `HomePage` (server) → `SearchView` → `Filters`/`PlaceList`/`MapView`."
    requirement: A11Y-02
    verification:
      - kind: build
        ref: "web: npm run typecheck && npm run lint"
        status: pass
      - kind: unit
        ref: "web: npm test -- --run (40 tests, 8 files)"
        status: pass
  - id: D5
    description: "The map stays `role=\"application\"` with no `tabindex`, and its aria-label is localized in both locales, still pointing at the list as the keyboard path."
    requirement: A11Y-03
    verification:
      - kind: build
        ref: "web/src/components/search/map-view.tsx: role=\"application\" kept, aria-label={t(locale, \"mapAriaLabel\")}, no tabindex"
        status: pass
  - id: D6
    description: "`label`, `formatValue`, `formatDate` and `familyLabel` honour the locale, and the locale survives `formatValue`'s array and nested-object branches."
    requirement: A11Y-02
    verification:
      - kind: unit
        ref: "web/src/lib/labels.test.ts#formats values in the requested language"
        status: pass
      - kind: unit
        ref: "web/src/lib/labels.test.ts#formats dates in the requested language"
        status: pass
      - kind: unit
        ref: "web/src/lib/search.test.ts#handicap families"
        status: pass
---

# Phase 11 Plan 01: Search-path i18n Summary

The search journey now speaks the reader's language: one dictionary in `lib/i18n.ts` owns every
message, `t` cannot reach a plural key, French counts 0 as singular, and the search page reads the
`locale` cookie server-side and renders the whole path — hero, filters, results heading, list,
load-more announcement, map label — from it.

## What changed

**Dictionary and typing (`lib/i18n.ts`).** The file now holds 125 keys per locale in three blocks:
the existing chrome, the search keys, and the record + auth/account keys that plans 11-05 and 11-06
will consume (declared once, here). `places`, `placesAdded` and `reviewsHeading` are the only plural
keys and are `{one, many}` objects in both locales. `StringMessageKey` and `PluralKey` are derived
from the `fr` column, so `t` accepts string keys only and `tPlural` is the sole route to a plural
word. `tPlural` returns `one` for `count === 1` and, in French only, for `count === 0`. `format`
replaces `{name}` placeholders and leaves unknown ones intact.

**Locale plumbing.** `HomePage` is now async and reads the cookie exactly as `layout.tsx` does
(`parseLocale((await cookies()).get(LOCALE_COOKIE)?.value)`), so the server renders the first paint
in the right language and `LocaleSwitch`'s `router.refresh()` is enough to flip it. The Suspense
fallback uses the new `searchLoading` key (the copy differs from `loading`).

**Search path.** `SearchView` takes `locale` and passes it to `Filters`, `PlaceList` and `MapView`.
Every French literal in those four files moved to `t()`; the load-more announcement is
`${next.length} ${tPlural(locale, "placesAdded", next.length)}.`, which drops the inline
`lieu${…x}` / `supplémentaire${…s}` hack. `Filters` iterates `FAMILY_KEYS` instead of
`Object.entries(FAMILY_LABELS)`, so the four handicap options render in the declared order.
`MapView` keeps `role="application"` and gains no `tabindex`: the list stays the keyboard path.

**Locale helpers.** `label(value, locale)` prefers `value[locale]`, then `value.fr`, then any value.
`formatValue(value, locale)` renders `notProvided`/`yes`/`no` from the dictionary and threads
`locale` through both recursive branches. `formatDate(iso, locale)` uses `en-GB` for English and
`fr-FR` for French. `lib/search.ts` replaces the French-only `FAMILY_LABELS` with the ordered
`FAMILY_KEYS` list and `familyLabel(family, locale = "fr")`, which falls back to the raw slug.

## Verification

```
cd web && npm run typecheck   → clean (tsc --noEmit)
cd web && npm test -- --run   → 8 files, 40 tests passed
cd web && npm run lint        → clean (eslint .)

uv run ruff check .           → All checks passed!
uv run ruff format --check .  → 210 files already formatted
uv run mypy                   → Success: no issues found in 74 source files
```

`pytest` was not run: no Python file changed. The unit tests cover the four plural cases the plan
named (`fr` 0/1/4, `en` 0/4 — plus `en` 1), `format` interpolation, the locale-aware
`label`/`formatValue`/`formatDate`, and `familyLabel`/`FAMILY_KEYS`.

The plan's key audit was run as a check, not a note: every `t(`/`tPlural(` key appearing in the
11-01, 11-05 and 11-06 `<action>` bodies and in `web/src` (90 distinct keys) is declared in
`MESSAGES.fr`, with zero misses:

```
comm -23 used.txt declared.txt   → (empty)
```

## Deviations from Plan

**1. [Rule 3 - blocking] `places/[slug]/page.tsx` updated to use `familyLabel`**
- **Found during:** Task 2, removing `FAMILY_LABELS`.
- **Issue:** the plan lists `filters.tsx` and `places/[slug]/page.tsx` as consumers of
  `FAMILY_LABELS` in its own context, but `files_modified` omits the record page. Deleting the record
  breaks `npm run typecheck` (`Module has no exported member 'FAMILY_LABELS'`).
- **Fix:** two lines — import `familyLabel` instead, render `{familyLabel(family)}`. The default
  `locale = "fr"` keeps today's output byte-identical, so the record page stays French until 11-05
  sweeps it, exactly as before.
- **Files modified:** `web/src/app/places/[slug]/page.tsx`

**2. [Plan example, not a deviation of intent] `familyLabel` keeps a default locale**
- **Found during:** the same edit.
- **Issue:** the plan's signature is `familyLabel(family: string, locale: Locale): string`. Without a
  default the record page must either read the cookie (11-05's job) or hardcode `"fr"` at the call
  site.
- **Fix:** `familyLabel(family: string, locale: Locale = "fr")`, matching the `label` / `formatValue` /
  `formatDate` defaults in the same module. 11-05 passes the real locale.

No other deviations: the dictionary, the plural rule, the cookie plumbing and the component sweep
were implemented as written.

## Threat notes

- T-11-01 (locale cookie tampering): unchanged — `parseLocale` still collapses anything but `"en"`
  to `fr`, and the value only selects a dictionary column.
- T-11-02 (interpolation): `format` inserts counts, page numbers and percentages only; `t()` output is
  never used as markup.
- T-11-SC (package installs): no dependency added; the existing vitest/tsc toolchain was used.
- No new endpoint, trust boundary or file-access pattern, so no new threat flag.

## Known stubs

None. The record and auth/account keys are declared but not yet consumed — they are the interface
contract for 11-05/11-06, not stubs.

## For the next plans

- **11-05 (record path) consumes, never declares.** The dictionary already holds every key it needs:
  `criterion`, `valueLabel`, `choose`, `exampleNumber`, `saving`, `save`, `publishing`,
  `publishReview`, `signInPrompt`, `toCompleteThisRecord`, `verifyToComplete`, `toLeaveAReview`,
  `verifyToReview`, `noCriteria`, `noTree`, `chooseValue`, `contributionSaved`, `contributionFailed`,
  `reviewPublished`, `reviewFailed`, `rating`, `yourReview`, `reviewPlaceholder`, `verifyDisabled`,
  `resendLink`, `sending`, `verificationSent`, `sendFailed`, `noReviews`, `anonymous`,
  `reviewPagination`, `previous`, `nextPage`, `backToSearch`, `backToSearchPlain`, `notYetRated`,
  `unspecifiedSource`, `completion`, `criteriaHaveValue`, `reviewCountLine`, `photos`,
  `accessibilitySection`, `completeThisRecord`, `contributionHelp`, `reviewsHeading` (plural),
  `leaveAReview`, `reviewHelp`, `pageOf`, `placeNotFoundTitle`, `placeNotFoundBody`.
- **Signature changes 11-05 must adapt to:** `label(value, locale = "fr")`,
  `formatValue(value, locale = "fr")`, `formatDate(iso, locale = "fr")` — the defaults mean callers
  keep compiling, so the sweep has to pass `locale` explicitly or the record page stays French
  silently. `FAMILY_LABELS` is gone; use `familyLabel(family, locale)`.
- **`places/[slug]/page.tsx` still has no cookie read.** It is the one server page that renders
  localized helpers with the default locale; 11-05 must add
  `parseLocale((await cookies()).get(LOCALE_COOKIE)?.value)` there (same as `page.tsx`/`layout.tsx`)
  and pass it to `formatValue`/`formatDate`/`familyLabel`/`label`.
- **`format(t(locale, "reviewsHeading"), {count})` is needed** for the "Avis (N)" heading: the
  plural object carries the `{count}` placeholder, so `tPlural` alone is not enough — interpolate the
  result.
- Things still hardcoded that 11-05/11-06 must resolve: the `metadata` title/description exports on
  `layout.tsx` and the `(auth)` pages (static SEO strings, deliberately out of scope), the
  `site-header` `aria-label={locale === "en" ? … : …}` inline ternary, and
  `not-found.tsx` (does not exist yet — 11-05 adds it).
- No `check:i18n` guard exists yet; it lands in 11-06 once every literal has moved. Until then a new
  hardcoded French string fails nothing.

## Self-Check: PASSED

- `web/src/lib/i18n.ts`, `web/src/lib/labels.ts`, `web/src/lib/search.ts` exist and export
  `t`/`tPlural`/`format`, `label`/`formatValue`/`formatDate`, `FAMILY_KEYS`/`familyLabel`.
- `.planning/phases/11-e2e-accessibility/11-01-SUMMARY.md` exists.
- Commit `819c389` is an ancestor of HEAD (`git merge-base --is-ancestor`); one commit measured from
  the plan ledger (`aa7923b..819c389`).
