---
phase: 05-auth-contribution
verified: 2026-10-27T22:32:00Z
status: passed
score: 6/6 must-haves verified
ticket: LET-10
branch: LET-10-auth-contribution
plan: 05-01-PLAN.md
requirements:
  AUTH-01: satisfied - POST /auth/register with duplicate and input validation
  AUTH-02: satisfied - login + access/refresh JWT, /refresh, /me
  AUTH-03: satisfied - user/admin roles; admin-only review moderation
  CONTRIB-01: satisfied - authenticated PUT of one accessibility value
  CONTRIB-02: satisfied - append-only contribution log + recomputed filled_rate
  REV-02: satisfied - authenticated review creation
gates:
  ruff_check: pass
  ruff_format_check: pass
  mypy: pass
  bandit: pass
  pytest: pass (166 passed, 93.52% line+branch locally; CI green with 5 private-data skips)
  alembic_current: "0006 (head)"
  pr_checks: pass (6/6)
gaps: []
warnings:
  - "The JWT secret defaults to a development value; production must set LETMEGETIN_JWT_SECRET."
  - "Auth endpoints are not rate-limited yet (planned for Phase 7 / gateway)."
  - "No password reset and no OAuth (post-MVP); a user who loses the password cannot recover it."
  - "Without LETMEGETIN_SMTP_HOST, verification emails are only written to the log, so a real deployment must configure SMTP."
  - "Referential edits remain CLI-only, so AUTH-03 is exercised on review moderation rather than on referential endpoints."
  - "A user's display_name is self-declared; reviews are attributed to it, never to the email."
deferred:
  - item: "Password reset and OAuth"
    addressed_in: "Post-MVP"
    evidence: "05-CONTEXT.md deferred list; no v1 requirement."
  - item: "Rate limiting on auth and contribution endpoints"
    addressed_in: "Phase 7 (public API)"
    evidence: "ROADMAP Phase 7: API key + rate-limited partner calls."
---

# Phase 5: Auth & Contribution Verification Report

**Phase goal (ROADMAP):** Create an account, contribute to records and post reviews.
**Ticket:** LET-10 · **Branch:** `LET-10-auth-contribution` · **PR:** #9
**Verified:** 2026-10-27T23:05:00Z
**Method:** goal-backward against the code, the live PostGIS dev container, migration `0005`, and
the GitHub PR checks; SUMMARY claims re-derived from tests and SQL.

## Requirement evidence

| Requirement | Evidence |
|---|---|
| AUTH-01 | `POST /auth/register` (201), duplicate 409, invalid email/short password 422/422; unit + integration tests. |
| AUTH-02 | Login returns access + refresh; `/refresh` rejects an access token (401); `/me` resolves the bearer; expired/tampered tokens rejected. |
| AUTH-03 | `users.role`; `require_admin` gates `PATCH /reviews/{id}` (403 for `user`, 200 for `admin`). |
| CONTRIB-01 | `PUT /places/{slug}/accessibility/{criterion_slug}` requires a bearer and upserts the value. |
| CONTRIB-02 | Each write appends a `contribution` row; the response carries the recomputed `filled_rate`. |
| REV-02 | `POST /places/{slug}/reviews` (auth, verified email) creates a published review; the average and count update on the detail. |
| Refresh revocation | `refresh_token` stores only a SHA-256 fingerprint; `/refresh` rotates (reuse → 401) and `/logout` revokes. |
| Email verification | `POST /auth/verify-email` consumes a `typ=verify` token; `/resend-verification` re-sends; writes return 403 until verified. |

## Sequence verified

Register → login → access token → contribution (value + log + rate) → review → admin hides it →
list/rating reflect the change. Anonymous contribution and review calls return 401.
