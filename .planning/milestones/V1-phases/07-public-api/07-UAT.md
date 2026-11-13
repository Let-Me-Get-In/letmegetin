---
status: complete
phase: 07-public-api
source: 07-01-PLAN.md
started: 2026-10-31T09:00:00Z
updated: 2026-10-31T09:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. API key CLI
expected: create prints the raw key once; list never shows it; revoke disables it; the database stores only the SHA-256 hash.
result: pass
source: automated
evidence: "Integration test: hash matches token_fingerprint, rpm stored, list hides the raw key, revoke sets active=false."

### 2. Key authentication and quotas
expected: a valid key gets its own limit and `X-RateLimit-*` headers; over-quota → 429 with `Retry-After`; invalid key → 401.
result: pass
source: automated
evidence: "Key with rpm=1: first /categories 200 with limit=1/remaining=0; second 429 + Retry-After; unknown key 401."

### 3. Redis limiter and cache
expected: the Redis backend shares the counter; the cache round-trips JSON.
result: pass
source: automated
evidence: "fakeredis tests: second hit denied; RedisCache set/get; NullCache never hits."

### 4. Referential cache
expected: a categories read populates `ref:{version}:categories` in Redis and the next read still succeeds.
result: pass
source: automated
evidence: "Integration test with a fake Redis client: key created under the current referential version."

### 5. OpenAPI
expected: `/openapi.json` lists the public paths and the `X-API-Key` security scheme; the committed schema does not drift.
result: pass
source: automated
evidence: "Unit test on app.openapi(); CI `openapi` job regenerates and diffs docs/openapi.json."

### 6. Backend suite
expected: 85% coverage floor and all tests green after the keys/limits/cache changes.
result: pass
source: automated
evidence: "186 pytest tests pass; ruff, mypy and bandit clean."

### 7. Web suite
expected: the BFF forwards the optional API key and the app still builds with the standalone output.
result: pass
source: automated
evidence: "25 Vitest tests pass; lint, typecheck and `next build` (standalone) pass."

### 8. Docker images
expected: the API and web images build.
result: pass
source: automated
evidence: "docker build --target api and --target web both succeed; the web image is a Next standalone build."

### 9. Compose stack
expected: `docker compose -p letmegetin-prod -f docker-compose.prod.yml up` serves the API `/health` and the web `/`; Redis is used for limits and cache.
result: pass
source: runtime
evidence: "api /health 200, /docs 200, /openapi.json 200, web / 200, BFF /categories 200; cache key ref:2:categories; key rpm=1 → 200 then 429 (Retry-After 60); invalid key 401."

### 10. CI
expected: lint, types, SAST, secrets, unit, tests, web, OpenAPI drift and image builds all pass.
result: pass
source: automated
evidence: "GitHub Actions run 41186751065: 9/9 jobs pass (including OpenAPI drift and Docker images)."

### 11. Idempotent writes
expected: the same `Idempotency-Key` + payload replays the stored contribution/review; a different payload is 409; an unchanged PUT does not duplicate the audit log; logout is 204 without a session.
result: pass
source: automated
evidence: "4 backend tests + 1 BFF test: replay 200/201, 409 on payload change, contribution log stays at 1, unchanged PUT without a key logs once, logout no-cookie 204."

### 12. Sliding-window limits and worker fallback
expected: the limiter counts a true sliding window, and the in-memory fallback divides the budget by the worker count.
result: pass
source: automated
evidence: "3 unit tests (memory allow/deny/reset, Redis fakeredis); the fallback uses max(1, limit // worker_count)."

### 13. Production guard and dependency hygiene
expected: production refuses the development JWT secret; images are pinned by digest; production dependencies have no known advisory.
result: pass
source: automated
evidence: "2 settings tests; Dockerfile FROM lines pinned to multi-arch digests; `npm audit --omit=dev` → 0 vulnerabilities (16 moderate remain dev-only)."

## Summary

total: 13
passed: 13
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
