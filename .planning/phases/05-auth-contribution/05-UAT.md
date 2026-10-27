---
status: complete
phase: 05-auth-contribution
source: 05-01-SUMMARY.md
started: 2026-10-27T21:45:00Z
updated: 2026-10-27T22:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Account creation and login
expected: Register → 201 with a public user shape; duplicate → 409; login → access + refresh; refresh → new pair; `/me` → the account; an access token used as refresh → 401.
result: pass
source: automated
evidence: "Integration test: 201/409/200/200/401; `/me` returns the email; no `password_hash` in the response."

### 2. Password and token edge cases
expected: scrypt hashes verify; malformed hashes fail; tokens reject a wrong kind, expiry and tampering.
result: pass
source: automated
evidence: "9 unit tests: roundtrip, malformed hashes, typ=refresh used as access, expired (ttl=-10), payload tampering."

### 3. Authenticated contribution
expected: `PUT /places/{slug}/accessibility/{criterion_slug}` bumps the value, appends one contribution row per call, and returns the recomputed `filled_rate`; anonymous → 401; unknown place/criterion → 404.
result: pass
source: automated
evidence: "filled_rate 0.5 after one of two criteria; two PUTs → one value row, two log rows; stored `false` after the second write."

### 4. Reviews
expected: An authenticated `POST /places/{slug}/reviews` creates a published review attributed to the display name; it appears in the list and moves the average.
result: pass
source: automated
evidence: "201 with author 'Alice'; list total 1; detail rating 4.0."

### 5. Admin moderation
expected: A `user` gets 403 on `PATCH /reviews/{id}`; an `admin` hides the review and it leaves the list and the average.
result: pass
source: automated
evidence: "403 for role=user; after promotion 200 status=hidden; list total 0; detail rating null."

### 6. CI green
expected: on PR #9, lint, typecheck, sast, secret-scan, unit and test all pass.
result: pass
source: automated
evidence: "GitHub Actions run 40591089274: 6/6 jobs pass."

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
