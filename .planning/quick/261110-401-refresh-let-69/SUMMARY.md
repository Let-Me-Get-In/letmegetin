---
status: complete
quick_id: 261110-401
slug: refresh-401
date: 2026-11-10
ticket: LET-69
---

# Summary — Remove the anonymous refresh 401

## Result

- `web/src/app/api/[...path]/route.ts` now returns `204 No Content` for a refresh
  without the httpOnly refresh cookie, instead of `401`.
- `web/src/lib/session.tsx` checks for a missing access token before `loadUser`, so an
  anonymous mount ends cleanly in the no-session state.
- The route test now asserts the anonymous `204` and still proves no upstream call.

## Verification

- `npx vitest run "src/app/api/[...path]/route.test.ts"` — 8 passed.
- `npx vitest run` — 9 files / 56 tests passed.
- `npm run lint` — clean (`check:i18n` 30 files).
- `npm run typecheck` — clean.
- `npm run build` — clean.
- Playwright on local `/` and `/landing`: refresh responses `204`, `204`; no refresh `401`.
  Local 502s and the MapLibre worker error come from the absent backend/tiles, unrelated.
