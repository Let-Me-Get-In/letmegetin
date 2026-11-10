---
quick_id: 261110-cff
slug: landing-page-let-64
date: 2026-11-10
ticket: LET-64
status: complete
---

# Landing page LET-64

## Goal

Ship the public landing page on `letmegetin.org` from the existing Next.js app, without a
second deploy: the apex serves marketing, `app.letmegetin.org` keeps the application.

## Tasks

1. Serve the landing from the same app and route by host (`proxy.ts`).
2. Build the record-first composition from the approved comp, with search as the primary action.
3. Add the data/open-source/API sections and the contribution CTA.
4. Wire SEO: canonical apex, production-only indexing, OG/Twitter metadata, robots and sitemap.
5. Add the apex host to Caddy and the production env example.
6. Verify at 1440 and 390, light and dark, then lint, typecheck, tests and build.

## Verification

- `npm run lint`, `npm run typecheck`, `npx vitest run`, `npm run build`.
- Local `next start` with `Host: letmegetin.org`: apex landing 200, app routes 301 to the app,
  `www` 301 to apex, canonical `https://letmegetin.org`, robots index.
- Playwright desktop/mobile screenshots: no horizontal overflow, one-row mobile header.
