---
phase: 05-auth-contribution
plan: 01
subsystem: accounts
tags: [auth, scrypt, jwt, contribution, reviews, moderation]
requires:
  - "Phase 4 places, reviews and filled_rate"
provides:
  - "users and contribution tables, review.user_id (migration 0005)"
  - "POST /api/v1/auth/register|login|refresh, GET /me"
  - "PUT /api/v1/places/{slug}/accessibility/{criterion_slug} (auth)"
  - "POST /api/v1/places/{slug}/reviews (auth), PATCH /api/v1/reviews/{id} (admin)"
affects:
  - "Phase 6 UI consumes auth, contribution and review endpoints"
  - "Phase 7 rate limiting wraps the auth endpoints"
tech-stack:
  added: []
  patterns:
    - "scrypt password hashing + HS256 JWT from the standard library"
    - "Stateless access/refresh tokens distinguished by a `typ` claim"
    - "Contribution as an append-only log beside the current value"
    - "Admin gate on the first sensitive action (review moderation)"
key-files:
  created:
    - src/letmegetin/core/security.py
    - src/letmegetin/domain/accounts/entities.py
    - src/letmegetin/domain/accounts/repositories.py
    - src/letmegetin/application/accounts/register.py
    - src/letmegetin/application/accounts/login.py
    - src/letmegetin/application/places/contribute.py
    - src/letmegetin/application/places/reviews.py
    - src/letmegetin/api/v1/auth.py
    - src/letmegetin/api/schemas/auth.py
    - migrations/versions/0005_auth_contribution.py
    - tests/unit/test_security.py
    - tests/unit/test_accounts.py
    - tests/integration/test_auth_contribution.py
  modified:
    - src/letmegetin/config.py
    - src/letmegetin/core/exceptions.py
    - src/letmegetin/domain/places/entities.py
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/api/deps.py
    - src/letmegetin/api/v1/places.py
    - src/letmegetin/api/v1/router.py
    - src/letmegetin/api/schemas/places.py
decisions:
  - "No auth dependency: scrypt and HMAC-SHA256 come from the standard library"
  - "Refresh tokens are stateless for the MVP (no server-side revocation)"
  - "Reviews expose display_name or 'Anonyme', never the email"
  - "PATCH /reviews/{id} is the admin-gated sensitive action (referential edits stay CLI-only)"
metrics:
  duration: "~1h20"
  completed: "2026-10-27"
  tests: "142 -> 165 (all passing)"
  coverage: "94.08 % line+branch"
status: complete
---

# Phase 5 Plan 1: Auth & Contribution Summary

Accounts are real: a user registers, logs in with an access/refresh pair, writes accessibility
values that are logged, and posts reviews. An admin can hide a review.

## What was built

### Accounts

- `users` table (email unique, scrypt hash, role, display name) and migration `0005`.
- Register normalizes the email, enforces an 8-character password and rejects duplicates (409).
- Login returns an access/refresh pair; `/refresh` accepts only a `typ=refresh` token; `/me`
  returns the account behind a bearer access token.
- `require_admin` gates the review moderation endpoint (403 for `role=user`).

### Contribution

- `PUT /places/{slug}/accessibility/{criterion_slug}` (auth) upserts
  `place_accessibility` with `{"value": …, "source": "user", "user_id": …}` and appends one
  `contribution` row per call.
- The response carries the recomputed `filled_rate` (re-read through `get_place`).
- Unknown place or criterion → 404; anonymous → 401.

### Reviews

- `POST /places/{slug}/reviews` (auth, rating 1-5) creates a published review attributed to the
  display name.
- `PATCH /reviews/{id}` (admin) hides or restores it; hidden reviews leave the list and the
  average immediately.

## Verification

- `ruff check`, `ruff format --check`, `mypy`, `bandit`: pass.
- `pytest`: 165 passed, 94.08 % line+branch (floor 85 %).
- `alembic upgrade head`: `0005 (head)`.

## Addendum — previously deferred items now closed

- **Refresh-token revocation and rotation**: migration `0006` adds `refresh_token` (SHA-256
  fingerprint, expiry, revoked flag). Login and refresh persist the fingerprint; `/refresh`
  checks it, revokes the presented token and issues a new pair; `/logout` revokes it.
- **Email verification**: `users.email_verified`, a `typ=verify` JWT, a mailer that logs the link
  in development and sends SMTP when `LETMEGETIN_SMTP_HOST` is set, `/verify-email` and
  `/resend-verification`. Contributions and review creation now require a verified address (403
  otherwise).
- Tokens carry a random `jti`, so two tokens issued in the same second are distinct.

## Deferred

- Password reset and OAuth.
- Auth rate limiting (Phase 7) and a non-default `LETMEGETIN_JWT_SECRET` in production.
