---
quick_id: 261110-401
slug: refresh-401
date: 2026-11-10
ticket: LET-69
status: complete
---

# Remove the anonymous refresh 401

## Goal

Stop `/api/v1/auth/refresh` from returning 401 and logging a console error for visitors
without a session, on the landing and every app page.

## Tasks

1. Return `204` from the Next BFF refresh route when no refresh cookie exists.
2. Treat a missing access token explicitly in `SessionProvider.refresh`.
3. Update the route test to assert the anonymous `204`.

## Verification

- `npx vitest run "src/app/api/[...path]/route.test.ts"`.
- `npx vitest run`, `npm run lint`, `npm run typecheck`, `npm run build`.
- Playwright local: `/` and `/landing` log refresh `204`, no refresh `401`.
