---
status: complete
phase: 06-frontend
source: 06-01-PLAN.md
started: 2026-10-30T20:00:00Z
updated: 2026-10-30T23:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Search page and BFF
expected: The home page renders the search UI; `/api/v1/categories` through the Next BFF returns the API payload.
result: pass
source: runtime
evidence: "GET / → 200 and contains 'Trouver un lieu vraiment accessible'; GET /api/v1/categories → 200 with the seeded categories."

### 2. Place record
expected: A seeded place renders its name, accessibility tree and completion block.
result: pass
source: runtime
evidence: "Imported one Acceslibre row (restaurant); API detail returned 4 groups and filled_rate 0.5; GET /places/restaurant-du-test-cdb08050 → 200 with the name and 'Complétude de la fiche'."

### 3. Auth through the BFF
expected: register 201; login 200 sets an httpOnly refresh cookie and returns only the access token; `/me` works; refresh rotates; logout revokes; refresh after logout → 401.
result: pass
source: runtime
evidence: "201 / 200 (cookie present, no refresh_token in the body) / 200 / 200 / 204 / 401."

### 4. Frontend checks
expected: `npm run lint`, `npm run typecheck`, `npm test -- --run`, `npm run build` all pass.
result: pass
source: automated
evidence: "ESLint clean; tsc clean; 14 Vitest tests pass; Next build succeeds (8 routes)."

### 5. Backend checks
expected: the additive `CriterionOut.id` keeps the suite green.
result: pass
source: automated
evidence: "166 pytest tests pass; ruff, mypy and bandit clean."

### 6. CI
expected: on PR #11, the six backend jobs plus the new web job pass.
result: pass
source: automated
evidence: "GitHub Actions run 41139499538: 7/7 jobs pass."

### 7. Accessibility review
expected: skip link, semantic headings, labelled controls, visible focus, status live regions, reduced-motion handling, map text alternative.
result: pass
source: manual
evidence: "Code review of the layout, forms, tree and map; keyboard paths on the list and forms. Not a full axe/Lighthouse run."

### 8. BFF security
expected: login sets an httpOnly/SameSite=Lax cookie and strips the refresh token; a cross-origin state change is rejected; refresh without the cookie is 401; logout clears the cookie.
result: pass
source: automated
evidence: "4 Vitest tests: cookie flags, no refresh token in the body, cross-origin 403 (no upstream call), 401 without cookie, Max-Age=0 on logout."

### 9. Write forms
expected: contribution and review forms show the auth/verification gates, send the right payload, and surface API errors.
result: pass
source: automated
evidence: "5 Vitest tests: anonymous/verify messages, PUT {value:true}, POST {rating:4, body}, 403 message."

### 10. Automated WCAG check
expected: the rendered accessibility tree has no WCAG 2.0/2.1 A/AA violations.
result: pass
source: automated
evidence: "axe-core run on the tree component: zero violations (color-contrast disabled, jsdom limitation)."

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
