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

- [x] **DATA-01**: Every criterion and filter carries at least one handicap family
- [x] **DATA-02**: Imported categories resolve to a grid (no silent NULL for `bibliotheque`/`musee`)
- [x] **DATA-03**: A duplicate review queue (0.60–0.90) supports merge/reject with an audit log
- [x] **DATA-04**: Coverage metrics by category/country are exportable

### Search

- [x] **SEARCH-01**: Multiple criterion filters combine with AND
- [x] **SEARCH-02**: Search filters by category
- [x] **SEARCH-03**: Results are ranked and paginated beyond 100 hits

### E2E & Accessibility

- [x] **E2E-01**: A browser e2e suite in a separate repo covers search, record, contribution and review
- [x] **A11Y-01**: A screen-reader audit of search and record is documented with fixes
- [x] **A11Y-02**: The UI ships fr/en strings with a persisted language
- [x] **A11Y-03**: The map has a usable non-visual path (list + keyboard)

| Requirement | Phase | Status |
|---|---|---|
| OPS-04 | Phase 8 | Partial (host cutover) |
| OPS-05 | Phase 8 | Complete |
| OPS-06 | Phase 8 | Complete |
| DATA-01 | Phase 9 | Complete |
| DATA-02 | Phase 9 | Complete |
| DATA-03 | Phase 9 | Complete |
| DATA-04 | Phase 9 | Complete |
| SEARCH-01 | Phase 10 | Complete |
| SEARCH-02 | Phase 10 | Complete |
| SEARCH-03 | Phase 10.1 | Complete |
| E2E-01 | Phase 11 | Complete |
| A11Y-01 | Phase 11 | Complete |
| A11Y-02 | Phase 11 | Complete |
| A11Y-03 | Phase 11 | Complete |

## v2.0 Requirements — Federated Data & Partners

**Defined:** 2026-11-13
**Output licence:** ODbL for the database and the open export; AGPL-3.0 for the code.

### Licence provenance

- [x] **LIC-01**: Every place row records the source and licence it came from, and every accessibility answer records the source that produced it
- [x] **LIC-02**: A row can be classified as redistributable to a given destination (OSM, a lov2 partner, the open export), and that rule is enforced at every point where rows leave the system
- [x] **LIC-03**: A row derived from OSM is never sent to a lov2 destination
- [x] **LIC-04**: Re-importing a source never overwrites a fresher contribution or a row that came from another source
- [x] **LIC-05**: Licence rules live in reviewed data, not in importer code

### Open export

- [ ] **EXP-01**: A partner can download an ODbL export of places, categories, criteria and answers, carrying stable ids and each row's origin id
- [ ] **EXP-02**: The export renders cumulative attribution (AccesLibre with source name and last-update date, OpenStreetMap, Overture) and documents the API and map as Produced Works

### AccesLibre round trip

- [ ] **PART-01**: AccesLibre can receive a lov2 feed of owned rows keyed on their identifiers, with categories and criteria expressed in their vocabulary, plus a mapping document listing every place of ours they cannot match and why
- [ ] **PART-02**: An operator can push our answers to the AccesLibre API idempotently, with conflict rules and provenance strong enough that a later import cannot overwrite a fresher community contribution

### OpenStreetMap

- [ ] **OSM-01**: An operator can import the France OSM extract's POIs as `source='osm'`, idempotently on the node/way id, mapped to our categories through reviewed tags
- [ ] **OSM-02**: An operator can publish our answers to OSM once the terms-of-service consent exists, following OSM's documented import and automated-edit policy (import plan, wiki page, community discussion, per-changeset comments, bot account)

### Overture

- [ ] **OVT-01**: A committed CSV maps Overture `basic_category` to our category slugs, with non-visitable labels deliberately emptied and documented
- [ ] **OVT-02**: The Overture × AccesLibre overlap is measured by category and reported, so the import volume is chosen on evidence rather than guesswork
- [ ] **OVT-03**: An operator can import Overture French places as `source='overture'` (GERS id as source_id), never overwriting an existing AccesLibre place, and a place with no matching category still imports

### Product

- [x] **PROD-01**: A place shows how well documented it is, on a stated threshold ladder with an accessible legend, and an undocumented place still appears in search and can be completed in place

## Future Requirements (after v2.0)

- Gamification: challenges, teams, contribution points, leaderboards
- Real-time messaging between contributors
- Native iOS/Android apps
- Full moderation back-office

## Out of Scope

| Feature | Reason |
|---------|--------|
| 1:1 copy of the historical database | The dump no longer exists; we rebuild an editable grid |
| Real-time chat (Crossbar) | Needless complexity for the core referential |
| Native mobile apps | API-first first, mobile later |
| Closed partner referential imports (Macif, La Poste, LocalEyes, HandiPlage) | No licence basis to redistribute or merge them |
| Google Places as a source | Its ToS forbids storing the data |

## Traceability (v2.0)

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIC-01 | Phase 12 | Complete |
| LIC-02 | Phase 12 | Complete |
| LIC-03 | Phase 12 | Complete |
| LIC-04 | Phase 12 | Complete |
| LIC-05 | Phase 12 | Complete |
| PROD-01 | Phase 13 | Complete |
| EXP-01 | Phase 14 | Pending |
| EXP-02 | Phase 14 | Pending |
| PART-01 | Phase 15 | Pending |
| PART-02 | Phase 15 | Pending |
| OSM-01 | Phase 16 | Pending |
| OSM-02 | Phase 16 | Pending |
| OVT-01 | Phase 17 | Pending |
| OVT-02 | Phase 17 | Pending |
| OVT-03 | Phase 17 | Pending |

**Coverage:**
- v2.0 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓
