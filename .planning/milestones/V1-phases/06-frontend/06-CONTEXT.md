# Phase 6: Next.js Frontend — Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

The public web app in `web/`, consuming the existing `/api/v1`:

- **Search**: map + list, text, proximity/radius, handicap family and criterion filters.
- **Record**: place details, accessibility tree with values and `filled_rate`, reviews, photos.
- **Account**: register, log in, verify email, profile.
- **Writes**: authenticated contribution and review from the UI.

Out of scope: e2e suite (separate repo), native mobile, admin console, payments, offline/PWA.
</domain>

<decisions>
## Decisions

- **Next.js (App Router) + TypeScript strict + Tailwind + MapLibre GL** with OSM raster tiles.
  Server Components by default; Client Components only for the map, forms and session.
- **BFF for auth**: Next route handlers proxy `/api/*` to FastAPI. The **refresh token lives in an
  httpOnly, Secure, SameSite=Lax cookie**; the access token stays in memory. No token in
  `localStorage`. One silent refresh on 401, then redirect to login.
- **No duplicate business logic**: the UI renders the API's `tree`, `filled_rate`, `rating` and
  `review_count`; it never recomputes accessibility.
- **Accessibility is the product**: WCAG 2.1 AA target — keyboard paths for map/list/filters,
  visible focus, labels, contrast, `prefers-reduced-motion`, no color-only status.
- **French first, English ready**: a small dictionary (`fr`/`en`) for UI strings; place labels come
  from the API's multilingual JSONB.
- **Map and list stay in sync**: selecting a pin highlights the card, and vice versa; geolocation
  is opt-in with a clear fallback to a city/address search.
- **Verified writes**: contribution and review forms are visible to all but disabled with a
  "verify your email" banner until `email_verified` is true.
- **Testing**: Vitest + Testing Library for the API client, auth guard and the filter/record
  components; no browser e2e in this repo.
- **CI**: add a `web` job (`npm ci`, lint, typecheck, test, build) to the existing workflow.
</decisions>

<canonical_refs>
- `.planning/REQUIREMENTS.md` — FRONT-01..04.
- `.planning/ROADMAP.md` — Phase 6 success criteria.
- `.planning/phases/03-places-search/03-CONTEXT.md` — place search and grid.
- `.planning/phases/04-record-reviews/04-CONTEXT.md` — tree, `filled_rate`, reviews, photos.
- `.planning/phases/05-auth-contribution/05-CONTEXT.md` — auth, contribution, moderation.
- API: `/api/v1/places`, `/places/{slug}`, `/places/{slug}/reviews`, `/auth/*`,
  `/places/{slug}/accessibility/{criterion}`, `/reviews/{id}`.
</canonical_refs>

<code_context>
- `web/` does not exist yet: this phase scaffolds it.
- The API runs on `http://localhost:8000`; `NEXT_PUBLIC_API_URL` points the BFF at it.
- The grid tree node shape is `{slug, label, type, position, handicap_families, children, value}`.
- Auth: access (15 min) + refresh (30 days, rotated, revocable); writes require a verified email.
</code_context>

<deferred>
- Browser e2e (separate repo), PWA/offline, map clustering at scale, OAuth, account deletion.
</deferred>

---
*Phase: 06-frontend*
