# Requirements: LetMeGetIn

**Defined:** 2026-10-26
**Core Value:** Let anyone know in seconds whether a place is truly accessible, through a structured accessibility record consumable by third parties.

## v1 Requirements

### Foundation & Ops

- [ ] **OPS-01**: The project starts with one command (`docker compose up` + `uv run`) with Postgres/PostGIS
- [ ] **OPS-02**: CI runs ruff, mypy, bandit, pytest (coverage floor)
- [ ] **OPS-03**: Schema migrations are managed by Alembic

### Referential

- [x] **REF-01**: The API lists categories with multilingual labels (fr/en/es/de/it)
- [x] **REF-02**: The API exposes the criteria tree per category (groups → criteria → options)
- [x] **REF-03**: The API lists accessibility filters (search) and official labels
- [x] **REF-04**: The initial seed is loaded from the reconstructed data (158 categories, 182 vocabulary rows, category-1 grid)
- [x] **REF-05**: A minimal admin/CLI can edit categories, criteria and options

### Places & search

- [x] **PLACE-01**: Users can search places by text and proximity (lat/lng/radius)
- [x] **PLACE-02**: Users can filter results by one or more accessibility criteria
- [x] **PLACE-03**: Users can view a place record (address, category, rating, photos)
- [x] **PLACE-04**: The record shows the accessibility tree with values and a completion rate
- [x] **PLACE-05**: A script imports a demo place dataset to populate search

### Reviews & contribution

- [x] **REV-01**: Users can read a place's reviews (rating 1–5 + text)
- [x] **REV-02**: Authenticated users can post a review
- [x] **CONTRIB-01**: Authenticated users can complete/edit a record's accessibility values
- [x] **CONTRIB-02**: Every contribution is logged and the completion rate is recomputed

### Auth

- [x] **AUTH-01**: Users can create an account (email + password)
- [x] **AUTH-02**: Users can log in and receive a JWT (access + refresh)
- [x] **AUTH-03**: `user` and `admin` roles gate sensitive actions

### Public API

- [x] **API-01**: Partners consume the API with an API key (rate-limited)
- [x] **API-02**: OpenAPI documentation is generated and published

### Frontend

- [x] **FRONT-01**: Users can search places (map + list + filters)
- [x] **FRONT-02**: Users can view a complete place record
- [x] **FRONT-03**: Authenticated users can contribute from the frontend
- [x] **FRONT-04**: Users can manage their account and profile

## v2 Requirements

### Gamification

- **GAME-01**: Corporate challenges with teams
- **GAME-02**: Contribution points and leaderboards
- **GAME-03**: Team messaging

### Integrations

- **INTG-01**: Partner referential imports (Macif, La Poste, LocalEyes, HandiPlage)
- **INTG-02**: Google Places / OpenStreetMap (Overpass) enrichment
- **INTG-03**: iOS/Android mobile apps

## Out of Scope

| Feature | Reason |
|---------|--------|
| 1:1 copy of the historical database | The dump no longer exists; we rebuild an editable grid |
| Real-time chat (Crossbar) | Needless complexity for the core referential |
| Native mobile apps | API-first first, mobile later |
| Full Flask-Admin-style back-office | Minimal admin in v1, enriched as needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| OPS-01 | Phase 1 | Pending |
| OPS-02 | Phase 1 | Pending |
| OPS-03 | Phase 1 | Pending |
| REF-01 | Phase 2 | Complete |
| REF-02 | Phase 2 | Complete |
| REF-03 | Phase 2 | Complete |
| REF-04 | Phase 2 | Complete |
| REF-05 | Phase 2 | Complete |
| PLACE-01 | Phase 3 | Complete |
| PLACE-02 | Phase 3 | Complete |
| PLACE-03 | Phase 4 | Complete |
| PLACE-04 | Phase 4 | Complete |
| PLACE-05 | Phase 3 | Complete |
| REV-01 | Phase 4 | Complete |
| REV-02 | Phase 5 | Complete |
| CONTRIB-01 | Phase 5 | Complete |
| CONTRIB-02 | Phase 5 | Complete |
| AUTH-01 | Phase 5 | Complete |
| AUTH-02 | Phase 5 | Complete |
| AUTH-03 | Phase 5 | Complete |
| API-01 | Phase 7 | Complete |
| API-02 | Phase 7 | Complete |
| FRONT-01 | Phase 6 | Complete |
| FRONT-02 | Phase 6 | Complete |
| FRONT-03 | Phase 6 | Complete |
| FRONT-04 | Phase 6 | Complete |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-26*
*Last updated: 2026-10-26 after initial definition*


## v1.1 Requirements

### Production & Ops

- [ ] **OPS-04**: The stack runs on a real host with TLS, production secrets and a documented runbook
- [x] **OPS-05**: Postgres and Redis backups run and a restore is tested
- [x] **OPS-06**: Monitoring covers `/health`, the 429 rate and Redis, with a retention job for idempotency keys

### Data quality

- [ ] **DATA-01**: Every criterion and filter carries at least one handicap family
- [ ] **DATA-02**: Imported categories resolve to a grid (no silent NULL for `bibliotheque`/`musee`)
- [ ] **DATA-03**: A duplicate review queue (0.60–0.90) supports merge/reject with an audit log
- [ ] **DATA-04**: Coverage metrics by category/country are exportable

### Search

- [ ] **SEARCH-01**: Multiple criterion filters combine with AND
- [ ] **SEARCH-02**: Search filters by category
- [ ] **SEARCH-03**: Results are ranked and paginated beyond 100 hits

### E2E & Accessibility

- [ ] **E2E-01**: A browser e2e suite in a separate repo covers search, record, contribution and review
- [ ] **A11Y-01**: A screen-reader audit of search and record is documented with fixes
- [ ] **A11Y-02**: The UI ships fr/en strings with a persisted language
- [ ] **A11Y-03**: The map has a usable non-visual path (list + keyboard)

| Requirement | Phase | Status |
|---|---|---|
| OPS-04 | Phase 8 | Partial (host cutover) |
| OPS-05 | Phase 8 | Complete |
| OPS-06 | Phase 8 | Complete |
| DATA-01 | Phase 9 | Pending |
| DATA-02 | Phase 9 | Pending |
| DATA-03 | Phase 9 | Pending |
| DATA-04 | Phase 9 | Pending |
| SEARCH-01 | Phase 10 | Pending |
| SEARCH-02 | Phase 10 | Pending |
| SEARCH-03 | Phase 10 | Pending |
| E2E-01 | Phase 11 | Pending |
| A11Y-01 | Phase 11 | Pending |
| A11Y-02 | Phase 11 | Pending |
| A11Y-03 | Phase 11 | Pending |
