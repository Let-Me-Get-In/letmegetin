---
status: complete
quick_id: 261110-cff
slug: landing-page-let-64
date: 2026-11-10
ticket: LET-64
---

# Summary — Landing page LET-64

## Result

The public landing now ships from the same Next.js app:

- `web/src/proxy.ts` rewrites the apex `/` to `/landing`, marks the marketing surface with
  `x-lmgi-surface`, redirects `www` and every app route on the apex with 301.
- `web/src/app/landing/page.tsx` and `web/src/components/landing/*` build the record-first page:
  hero with search, real record card, four handicap families, open-data counts, API example,
  contribution CTA and marketing header/footer.
- `web/src/app/layout.tsx` selects the marketing or app chrome from the request header.
- SEO: apex canonical, `index` only on the apex production host, OG/Twitter metadata,
  production-only sitemap, and `robots` that disallows the app surfaces.
- `deploy/vps/Caddyfile` serves `ROOT_DOMAIN` and redirects `www`; `deploy/.env.prod.example`
  gains `ROOT_DOMAIN`.
- `PRODUCT.md`, `DESIGN.md` and the landing surface brief record the product, visual system and
  direction contract.

## Verification

- `cd web && npm run lint` — eslint + check:i18n, 30 files, no French literal.
- `cd web && npm run typecheck` — clean.
- `cd web && npx vitest run` — 9 files, 56 tests passed.
- `cd web && npm run build` — clean; `/landing` and the proxy are emitted.
- Local `next start` checks: apex 200 with landing, `x-middleware-rewrite: /landing`,
  `robots: index, follow`, canonical `https://letmegetin.org`; app host keeps the app;
  apex `/places/x` 301 to the app; `www` 301 to apex.
- Playwright 1440×900 and 390×844, light and dark: no horizontal overflow; mobile header is one row.

## Notes

- The sitemap lists the landing only. Listing the 600k+ place pages needs an API slugs endpoint;
  tracked separately as noted in the LET-64 ticket.
- The landing search submits `q` with a Paris default centre because the current app search is
  geo-based; national query search is a follow-up.
- Pre-existing duplicate-matcher changes in the backend were left uncommitted and untouched.
