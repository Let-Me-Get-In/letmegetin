---
gsd_state_version: "1.0"
milestone: v2.0
current_phase: 13
current_phase_name: Documented-place visualisation
status: planning
stopped_at: Phase 12 complete, ready to plan Phase 13
last_updated: "2026-11-13T12:59:19.900Z"
last_activity: 2026-11-13
last_activity_desc: Phase 12 complete, transitioned to Phase 13
state_head: 4d37a8a2dbf9d9bed228c6261d165fd0d3f11625
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 5
  completed_plans: 5
  percent: 17
milestone_name: Federated Data & Partners
---

# State: LetMeGetIn

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-13)

**Core value:** Let anyone know in seconds whether a place is truly accessible.
**Current focus:** Phase 13 — Documented-place visualisation

## Current Position

Phase: 13 — Documented-place visualisation
Plan: Not started
Status: Ready to plan
Last activity: 2026-11-13 — Phase 12 complete, transitioned to Phase 13


## Quick Tasks Completed

| ID | Date | Task | Status |
| --- | --- | --- | --- |
| 261110-cff | 2026-11-10 | LET-64 — public landing on letmegetin.org | complete |
| 261110-401 | 2026-11-10 | LET-69 — anonymous refresh 401 | complete |

## Performance Metrics

- Requirements: 26 v1
- Phases: 7
- Linear tickets: LET-5..LET-12
- Plans completed: 18
- Phases complete: V1 7/7; V1.1 4/4 (Phase 9 verified on 2026-11-09; Phase 11 closed)

## Accumulated Context

### Decisions

- FastAPI + SQLAlchemy 2 async + PostGIS.
- Next.js (App Router) + TS + Tailwind + MapLibre.
- Reconstructed seed (no dump); category-1 grid as the base.
- Backend + frontend monorepo; e2e in a separate repo later.
- Linear team `LET`, tickets `LET-<n>` at the start of branch/commit/PR (`commit-msg` hook).
- GSD `branching_strategy = none` (no `gsd/phase-…` branches).
- Public repo under the `Let-Me-Get-In` GitHub organization; all public artifacts in English.
- Handicap families are reviewed data (`data/referential/families.csv`), not code: `families sync` fills only the empty rows and `families audit` is the DATA-01 gate.
- Acceslibre categories are reviewed data (`data/referential/acceslibre_categories.csv`, 260 mapped / 131 reviewed gaps): resolution is alias → exact category slug → ordered `category_mapping`, and `place.source_category` keeps the raw value for `import report` (DATA-02 gate).
- Duplicates stay soft: the importer persists its 0.60–0.90 candidate on `place.duplicate_of_id`; `duplicates merge` reuses the importer's writes (canonical_id + alias + merge log) and `duplicates reject` keeps both rows — both append a `place_review_decision` row so rejections are auditable too (DATA-03).
- Coverage (`admin coverage --format csv`) is read-only and counts each real place once (canonical rows excluded), naming unresolved categories instead of dropping them (DATA-04).
- The `category` filter resolves the slug to an id in the API layer (`CategoryRepo.get_by_slug`, 422 on miss) and filters the indexed `place.category_id`; the domain port never sees a slug (SEARCH-02).
- Multiple criterion filters combine with AND: one `EXISTS` per distinct id (`dict.fromkeys`) instead of one `criterion_id IN (...)`, so each added id narrows. The change is published in `docs/public-api.md` and the OpenAPI description, because third parties that relied on the old union are affected (SEARCH-01).
- Search ordering is total: `ORDER BY distance, place.id`. Distance ties are routine (one address, several activities) and Postgres may return tied rows in any order, so `LIMIT/OFFSET` without the primary-key tie-breaker duplicates or drops rows at a page boundary (SEARCH-03).
- Pagination is `offset` (cap 10 000) plus an `X-Has-More` header, not an envelope or a cursor: the response body stays a bare JSON array for live consumers. `has_more` comes from a `limit + 1` fetch trimmed in the application layer — no COUNT over 634k rows (SEARCH-03).
- Interface text lives in one dictionary (`web/src/lib/i18n.ts`, `fr` column is the reference and stays byte-identical to the literals it replaced — the e2e suite text-selects them). Record and auth/account keys are declared there once, by 11-01; plans 11-05/11-06 consume keys and never declare any (A11Y-02).
- A plural key is a `{one, many}` object in every locale; `t` is typed to string-valued keys only, so a plural word can only come from `tPlural`. French counts 0 as singular (`0 lieu`), English does not (`0 places`) — the rule lives in `tPlural`, never at a call site (A11Y-02).
- The `locale` cookie is read once per server render (`layout.tsx` for `<html lang>`, `page.tsx` for the page tree) and passed down as a prop; client components never read the cookie, so there is one source of truth and no hydration mismatch (A11Y-02).
- Handicap families render from the ordered `FAMILY_KEYS` list plus `familyLabel(family, locale)`, not from `Object.entries` over a label record: the filter order is declared, not dictionary-order (A11Y-02).
- The e2e account is seeded by `admin user ensure`, not by the register endpoint: registration sends a verification email a headless suite cannot confirm. The password is never a CLI option — it comes from `LETMEGETIN_USER_PASSWORD` or a hidden prompt, because an option value lands in argv, `ps` and shell history (E2E-01).
- An idempotent account seed verifies, never overwrites: an existing account is checked against the supplied password and a mismatch is a `DomainError` (exit 1). A silent skip would leave the e2e suite holding a credential the operator believes they just set (E2E-01).
- Account commands use a commit-only runner (`_run_user_admin`, like `_run_api_key_admin`), not `_run_admin`: the latter bumps the referential version and rebuilds the category grids, which accounts do not touch (E2E-01).
- The record path reads the locale the same way the search path does: the server page reads the cookie once and passes `locale` as a required prop; the route-level `not-found.tsx` is async and reads it too. `VerifyBanner` requires `locale`, and the still-client account page passes `DEFAULT_LOCALE` until 11-06 gives it a server-resolved one (A11Y-02).
- A `<select>` whose value is persisted submits data, never display text: option criteria submit the option **slug** (booleans `oui`/`non`), because `contribute` stores the value verbatim and a label would freeze the interface language into the record (A11Y-02).
- Strings that are not display copy stay literals and are documented for the 11-06 guard: the `#avis` anchor fragment in pagination hrefs, the `/5` rating numerals, and the `oui`/`non` protocol values (A11Y-02).
- `check:i18n` is an AST guard, not a text grep: it flags French literals in **any** position (JSX text, JSX-expression literals, call arguments) because the real French in this codebase lives in expressions. Its exclusions are the rule, not a concession: non-display attributes (`href`, `className`, `id`, `key`, `value`, `type`, `role`, `name`, `htmlFor`, `aria-labelledby`, `data-*`), `*.test.*`, the `metadata` export, and the key argument of `t()`/`tPlural()`. `aria-label` is scanned because it is copy (A11Y-02).
- The guard is chained into `npm run lint` (`eslint . && node scripts/check-i18n.mjs`) instead of getting its own CI step, because the `web` job already runs lint: the guard costs no workflow change and cannot drift out of CI (A11Y-02).
- A page that needs the locale is an async server component reading the cookie, rendering a client view with `locale` as a required prop (`account/page.tsx` → `account-view.tsx`). No client component reads the cookie, so both `VerifyBanner` render sites get a real locale (A11Y-02).
- A write spec guards one helper call (`skipWithoutCredentials`) before its first navigation: production (`E2E_READ_ONLY`) skips it, a missing credential on push-to-main/dispatch (`E2E_REQUIRE_AUTH`) **throws** instead of skipping, and a credless fork PR skips — so `auth-gate.spec.ts` turns a lost secret into a red run (E2E-01).
- Write specs are chromium-only (the `mobile` project's `testIgnore`) and set `retries: 0`: one desktop click-path and at most one contribution and one review per run, because a retry would post twice (E2E-01).
- A spec that needs a populated form walks the search results in order and fails with a named fixture message ("seed a place with a grid or widen the search") rather than taking the first row and blundering past an absent `#criterion` (E2E-01).
- The authenticated e2e credentials are GitHub Actions secrets **in the e2e repo** (`E2E_USER_EMAIL`/`E2E_USER_PASSWORD`), consumed only by the development job; `LETMEGETIN_USER_PASSWORD` stays an operator shell variable. Nothing reaches the app runtime or the config repo (E2E-01).
- The e2e axe gate is **report-only** (`AXE_STRICT` unset) because every serious/critical finding lives in the app repo, which one e2e-repo commit cannot touch: the scan writes `test-results/axe-violations.json` (`{ scanned, seriousCriticalCount, violations }`, each violation tagged with its page) as the stated input of the follow-up app-repo fix, which then flips `AXE_STRICT=1` (A11Y-01).
- The one serious axe finding is `link-in-text-block` on the search page: the MapLibre **attribution link** (2.02:1 contrast, no underline). It is the map library's control, so the fix is a CSS override in `web/`, not a component rewrite (A11Y-01).
- The map assertion matches `/list/i`, not `/liste/i`: the label is localized, and a case-insensitive `list` is a substring of both `liste` and `list`, so one assertion covers both locales — while `tabindex="0"` stays refused, because localizing the label did not make the map a keyboard destination (A11Y-03).
- An axe scan waits for the last client-only thing to hydrate (the map) before running: a half-rendered page reports zero violations, and an artifact with a quiet zero would send the fix plan after nothing.

### Pending Todos

- Curate the vocabulary beyond the import: promote entries and translate labels (en/es/de) by hand.

### Blockers/Concerns

- The exact per-category grid is not recoverable; base + extension + admin.
- **The authenticated e2e journeys are written but unproven**: `contribution.spec.ts` and
  `review.spec.ts` need app PR #33 deployed to development and the verified account seeded on the
  host, then mirrored as the e2e repo secrets. Until then they report skipped locally and would fail
  on `main` under `E2E_REQUIRE_AUTH=true` (by design).
- **The human VoiceOver/NVDA pass is outstanding**, so A11Y-01 is not complete: the protocol and the
  blank sheet exist in the e2e repo (`docs/screen-reader-audit*.md`), the pass does not.
- **A full e2e run can trip the app's own public rate limit** (60 rpm per IP on `/api/v1/places`): a
  back-to-back run intermittently renders "Rate limit exceeded" and fails unrelated read-only specs.
  Run the gate as a first run after a ~70 s cooldown; options and evidence in
  `.planning/phases/11-e2e-accessibility/deferred-items.md`.

## Session Continuity

Last session: 2026-11-13T11:25:22.176Z
Stopped at: Phase 12 complete, ready to plan Phase 13
Resume file: .planning/phases/12-licence-provenance/12-01-PLAN.md

## Known debt

- **Test isolation**: the integration tests assume the dev `place` table holds
  only their fixtures. The national AccesLibre load (634 931 places, 6 Nov 2026)
  now lives in that same database, so five search tests fail locally while CI
  stays green (empty database). Fix: point the suite at a dedicated
  `letmegetin_test` database. Decided, not done.

### Browser UAT — dev, 2026-11-06 (`d9665bd`, 634 962 places)

Verified with Playwright on `https://app.dev.letmegetin.org`:

- Search returns real places sorted by distance (5 km around Paris → 100 first hits).
- **"Voir plus" works end to end**: 100 → 200 entries, heading "200 lieux", and the live
  region announces "100 lieux supplémentaires." — the a11y fix is effective.
- Map renders with markers; `role="application"` carries an aria-label pointing at the list.

Three defects found, none fixed yet:

1. **Category labels are Italian.** The select shows "Studio contabile", "Aeroporto",
   "Negozio di antiquariato": `categories.json` carries only `it` labels, so a French UI
   lists Italian categories. A 158-row translation, not a code change.
2. **MapLibre worker fails to load** — two console errors per search page; the map still
   renders (markers are drawn) but vector tiles are degraded.
3. **`/api/v1/auth/refresh` logs a 403 on every anonymous page load.** The session bootstrap
   calls refresh unconditionally; the browser records a failed request for every visitor.

Also confirmed absent at that date: **no language switcher** — `layout.tsx` hardcoded `lang="fr"`, which
made A11Y-02 (fr/en persisted) unimplemented. Superseded on this branch by `4657b6f`
(`LocaleSwitch` + cookie + `lang` from the cookie) and by 11-01 (the search path renders from the
dictionary); A11Y-02 now needs the record path (11-05) and the auth/account pages (11-06) — both landed, and `check:i18n` guards the result.
