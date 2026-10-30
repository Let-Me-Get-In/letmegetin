---
phase: 06-frontend
verified: 2026-10-30T23:45:00Z
status: passed
score: 4/4 must-haves verified
ticket: LET-11
branch: LET-11-frontend-app
plan: 06-01-PLAN.md
requirements:
  FRONT-01: satisfied - search by text/radius/family, map + list, criterion filters (category-scoped)
  FRONT-02: satisfied - record with tree, filled_rate, reviews and photos
  FRONT-03: satisfied - authenticated contribution form, gated on verified email
  FRONT-04: satisfied - register/login/verify/profile/logout
gates:
  ruff_check: pass
  ruff_format_check: pass
  mypy: pass
  bandit: pass
  pytest: pass (166 passed)
  web_lint: pass
  web_typecheck: pass
  web_tests: pass (14 Vitest tests)
  web_build: pass (Next 16 production build)
  alembic_current: "0006 (head)"
  pr_checks: pass (7/7, including the new web job)
gaps: []
warnings:
  - "No automated axe/Lighthouse run: the accessibility review is a code review plus keyboard checks."
  - "The map uses the public OpenStreetMap tile server; a production tile provider is required before launch."
  - "Criterion filters require selecting a category first, because the API endpoint is category-scoped."
  - "The refresh cookie is SameSite=Lax and httpOnly; there is no separate CSRF token, acceptable for a same-origin JSON BFF but to revisit if the surface grows."
  - "No browser e2e in this repo (deferred to a separate repo), so the contribution/review submissions are covered by the API tests and the form tests, not by a browser."
  - "The map's screen-reader experience relies on the parallel list; it has not been tested with a real screen reader."
deferred:
  - item: "Browser e2e (search, record, contribution, review)"
    addressed_in: "Separate e2e repository"
    evidence: "AGENTS.md: e2e later, separate repo."
  - item: "PWA/offline, OAuth, account deletion, map clustering at scale"
    addressed_in: "Post-v1"
    evidence: "06-CONTEXT.md deferred list."
---

# Phase 6: Next.js Frontend Verification Report

**Phase goal (ROADMAP):** Complete user journey (search, record, contribution, account).
**Ticket:** LET-11 · **Branch:** `LET-11-frontend-app` · **PR:** #11
**Verified:** 2026-10-30T23:45:00Z
**Method:** goal-backward against the code, the live API + Next dev server, the importer, the
database, and the GitHub PR checks. The runtime checks were performed against the seeded dev
PostGIS database.

## Requirement evidence

| Requirement | Evidence |
|---|---|
| FRONT-01 | Home renders the map/list/filters; `?q&lat&lng&radius&family&filters` is the URL contract; category-scoped criterion filters; geolocation with a fallback. |
| FRONT-02 | `/places/{slug}` is server-rendered from the API; the tree, `filled_rate`, per-family scores, reviews and photos are displayed. Runtime: imported place → 200 with 4 groups and 50% completion. |
| FRONT-03 | Contribution form is present on the record, requires a verified account, PUTs one criterion and refreshes the record. |
| FRONT-04 | Register/login/verify/account/logout; the refresh token is an httpOnly cookie set by the BFF, the access token stays in memory. Runtime: full auth sequence through the BFF. |

## Sequence verified

Search page → BFF categories → imported place → record → register → login (cookie) → `/me` →
refresh → logout → refresh rejected (401). The backend suite and the web build were re-run after
the additive `CriterionOut.id` change.
