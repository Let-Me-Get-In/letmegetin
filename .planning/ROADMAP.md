# Roadmap: LetMeGetIn

## Overview

Modern rewrite of the collaborative accessible-places guide: normalized referential + public FastAPI API + Next.js frontend. V1 = the product core (referential, search, record, contribution), shipped. V1.1 = production readiness, data quality, search quality, e2e and accessibility. Gamification, integrations and mobile are deferred.

## Phases

### Phase 1: Foundation & CI
**Goal:** A FastAPI + Postgres/PostGIS + Alembic + CI skeleton that starts and passes.
**Mode:** mvp
**Ticket:** LET-6
**Requirements:** OPS-01, OPS-02, OPS-03
**Success Criteria**:
1. `docker compose up -d` starts PostGIS and the API serves `GET /health` → 200.
2. `uv run alembic upgrade head` creates the schema.
3. `uv run pytest`, `uv run ruff check .` and `uv run mypy` pass locally and in CI.

### Phase 2: Referential & seed
**Goal:** The API exposes categories, the criteria tree and filters from the reconstructed seed.
**Mode:** mvp
**Ticket:** LET-7
**Requirements:** REF-01, REF-02, REF-03, REF-04, REF-05
**Success Criteria**:
1. `uv run python scripts/build_referential.py` produces the seed JSON.
2. `uv run python -m letmegetin.seed` loads 158 categories, 182 vocabulary rows and the category-1 grid.
3. `GET /api/v1/categories` and `GET /api/v1/categories/{slug}/criteria` return multilingual labels.
4. `GET /api/v1/filters` returns the 52 filters + official labels.
5. A minimal admin/CLI can add/edit a criterion.

**Plans:** 1 plan
Plans:
- [x] 02-01-PLAN.md — Curate the 182-label vocabulary into criterion_vocabulary, add the editable category-to-criteria mapping and the Typer admin CLI, then prove the multilingual reads

### Phase 3: Places & search
**Goal:** Search places by text, proximity and accessibility filters.
**Mode:** mvp
**Ticket:** LET-8
**Requirements:** PLACE-01, PLACE-02, PLACE-03, PLACE-04, PLACE-05
**Success Criteria**:
1. A script imports a demo place dataset.
2. `GET /api/v1/places?lat=&lng=&radius=&q=&filters=` returns distance-sorted results.
3. Criterion filters narrow the results correctly.
4. `GET /api/v1/places/{slug}` returns the full record (address, category, rating).

### Phase 4: Record & reviews (read)
**Goal:** View a complete accessibility record and its reviews.
**Mode:** mvp
**Ticket:** LET-9
**Requirements:** PLACE-03, PLACE-04, REV-01
**Success Criteria**:
1. The record returns the accessibility tree (groups → criteria → options) with values.
2. The completion rate (`filled_rate`) is computed.
3. Reviews are paginated and readable.

### Phase 5: Auth & contribution
**Goal:** Create an account, contribute to records and post reviews.
**Mode:** mvp
**Ticket:** LET-10
**Requirements:** AUTH-01, AUTH-02, AUTH-03, CONTRIB-01, CONTRIB-02, REV-02
**Success Criteria**:
1. Sign-up + JWT login (access/refresh).
2. An authenticated user completes a record → `accessibility_value` updated + `contribution` logged.
3. The completion rate is recomputed.
4. An authenticated review is created.
5. `admin` roles protect referential edits.

### Phase 6: Next.js frontend
**Goal:** Complete user journey (search, record, contribution, account).
**Mode:** mvp
**Ticket:** LET-11
**Requirements:** FRONT-01, FRONT-02, FRONT-03, FRONT-04
**Success Criteria**:
1. Home + map/list search with filters.
2. Place record with accessibility tree and reviews.
3. Contribution from the frontend (auth required).
4. Account/profile management.

### Phase 7: Public API & deployment
**Goal:** Open the API to partners and deploy.
**Mode:** mvp
**Ticket:** LET-12
**Requirements:** API-01, API-02
**Success Criteria**:
1. An API key authenticates and rate-limits partner calls.
2. OpenAPI docs are published and up to date.
3. The application is deployed (docker/CI) and reachable.

## Progress

| Phase | Ticket | Status | Completed |
|-------|--------|--------|-----------|
| 1. Foundation & CI | LET-6 | Complete | 2026-10-27 |
| 2. Referential & seed | LET-7 | Complete | 2026-10-27 |
| 3. Places & search | LET-8 | Complete | 2026-10-27 |
| 4. Record & reviews (read) | LET-9 | Complete | 2026-10-27 |
| 5. Auth & contribution | LET-10 | Complete | 2026-10-27 |
| 6. Next.js frontend | LET-11 | Complete | 2026-10-30 |
| 7. Public API & deployment | LET-12 | Complete | 2026-10-31 |

---
*Created: 2026-10-26*


## V1.1 — Production & Quality

### Phase 8: Production deployment & operations
**Goal:** Run the stack on a real host with TLS, secrets, backups, monitoring and retention.
**Mode:** mvp
**Ticket:** LET-23
**Requirements:** OPS-04, OPS-05, OPS-06
**Success Criteria**:
1. A real host serves the API and web over TLS with production secrets.
2. Postgres and Redis backups run and a restore is tested.
3. `/health`, the 429 rate and Redis availability are monitored/alerts.
4. A retention job purges `idempotency_key` and stale rows; a runbook documents it.

### Phase 9: Data quality & curation
**Goal:** Make the referential trustworthy: families, categories, duplicates and coverage.
**Mode:** mvp
**Ticket:** LET-24
**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04
**Success Criteria**:
1. Every criterion and filter carries at least one handicap family.
2. Imported categories resolve (no `bibliotheque`/`musee` NULL) and the mapping is auditable.
3. A duplicate review queue exposes 0.60–0.90 matches with merge/reject actions and a log.
4. Coverage metrics (by category/country) are exposed as an export or admin report.

### Phase 10: Search quality
**Goal:** Search narrows correctly and scales past the MVP limit.
**Mode:** mvp
**Ticket:** LET-25
**Requirements:** SEARCH-01, SEARCH-02, SEARCH-03
**Success Criteria**:
1. Multiple criterion filters combine with AND (narrowing, not widening).
2. Search filters by category.
3. Results are ranked and paginated beyond 100 hits, with stable ordering.

### Phase 11: E2E & accessibility
**Goal:** Prove the user journey in a browser and with assistive technology.
**Mode:** mvp
**Ticket:** LET-26
**Requirements:** E2E-01, A11Y-01, A11Y-02, A11Y-03
**Success Criteria**:
1. A Playwright suite in a separate repo covers search, record, contribution and review in CI.
2. A screen-reader audit of search and record is documented and blocking issues are fixed.
3. The UI ships fr/en strings with a persisted language.
4. The map has a usable non-visual path (list + keyboard) validated by the audit.

## V1.1 Progress

| Phase | Ticket | Status | Completed |
|-------|--------|--------|-----------|
| 8. Production deployment & operations | LET-23 | Complete | 2026-11-01 |
| 9. Data quality & curation | LET-24 | Pending | — |
| 10. Search quality | LET-25 | Pending | — |
| 11. E2E & accessibility | LET-26 | Pending | — |
