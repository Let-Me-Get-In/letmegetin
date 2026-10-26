# Requirements: LetMeGetIn

**Defined:** 2026-10-26
**Core Value:** Let anyone know in seconds whether a place is truly accessible, through a structured accessibility record consumable by third parties.

## v1 Requirements

### Foundation & Ops

- [ ] **OPS-01**: The project starts with one command (`docker compose up` + `uv run`) with Postgres/PostGIS
- [ ] **OPS-02**: CI runs ruff, mypy, bandit, pytest (coverage floor)
- [ ] **OPS-03**: Schema migrations are managed by Alembic

### Referential

- [ ] **REF-01**: The API lists categories with multilingual labels (fr/en/es/de/it)
- [ ] **REF-02**: The API exposes the criteria tree per category (groups → criteria → options)
- [ ] **REF-03**: The API lists accessibility filters (search) and official labels
- [ ] **REF-04**: The initial seed is loaded from the reconstructed data (158 categories, 182 criteria, category-1 grid)
- [ ] **REF-05**: A minimal admin/CLI can edit categories, criteria and options

### Places & search

- [ ] **PLACE-01**: Users can search places by text and proximity (lat/lng/radius)
- [ ] **PLACE-02**: Users can filter results by one or more accessibility criteria
- [ ] **PLACE-03**: Users can view a place record (address, category, rating, photos)
- [ ] **PLACE-04**: The record shows the accessibility tree with values and a completion rate
- [ ] **PLACE-05**: A script imports a demo place dataset to populate search

### Reviews & contribution

- [ ] **REV-01**: Users can read a place's reviews (rating 1–5 + text)
- [ ] **REV-02**: Authenticated users can post a review
- [ ] **CONTRIB-01**: Authenticated users can complete/edit a record's accessibility values
- [ ] **CONTRIB-02**: Every contribution is logged and the completion rate is recomputed

### Auth

- [ ] **AUTH-01**: Users can create an account (email + password)
- [ ] **AUTH-02**: Users can log in and receive a JWT (access + refresh)
- [ ] **AUTH-03**: `user` and `admin` roles gate sensitive actions

### Public API

- [ ] **API-01**: Partners consume the API with an API key (rate-limited)
- [ ] **API-02**: OpenAPI documentation is generated and published

### Frontend

- [ ] **FRONT-01**: Users can search places (map + list + filters)
- [ ] **FRONT-02**: Users can view a complete place record
- [ ] **FRONT-03**: Authenticated users can contribute from the frontend
- [ ] **FRONT-04**: Users can manage their account and profile

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
| REF-01 | Phase 2 | Pending |
| REF-02 | Phase 2 | Pending |
| REF-03 | Phase 2 | Pending |
| REF-04 | Phase 2 | Pending |
| REF-05 | Phase 2 | Pending |
| PLACE-01 | Phase 3 | Pending |
| PLACE-02 | Phase 3 | Pending |
| PLACE-03 | Phase 3 | Pending |
| PLACE-04 | Phase 3 | Pending |
| PLACE-05 | Phase 3 | Pending |
| REV-01 | Phase 4 | Pending |
| REV-02 | Phase 4 | Pending |
| CONTRIB-01 | Phase 5 | Pending |
| CONTRIB-02 | Phase 5 | Pending |
| AUTH-01 | Phase 5 | Pending |
| AUTH-02 | Phase 5 | Pending |
| AUTH-03 | Phase 5 | Pending |
| API-01 | Phase 7 | Pending |
| API-02 | Phase 7 | Pending |
| FRONT-01 | Phase 6 | Pending |
| FRONT-02 | Phase 6 | Pending |
| FRONT-03 | Phase 6 | Pending |
| FRONT-04 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-26*
*Last updated: 2026-10-26 after initial definition*
