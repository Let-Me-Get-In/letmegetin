# LetMeGetIn

## What This Is

LetMeGetIn is the modern rewrite of **Jaccede**, the collaborative guide to places accessible to people with disabilities (2002–2024). It exposes a **normalized accessibility referential** (place categories, typed hierarchical criteria, official labels) through a **public FastAPI API**, consumed by third parties and by our own Next.js frontend.

## Core Value

Let anyone know in seconds whether a place is truly accessible — through a structured, reliable accessibility record that any site or app can consume.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Referential: categories, typed hierarchical criteria, filters, official labels exposed by the API
- [ ] Seed reconstructed from the Jaccede archives (158 categories, 182 criteria, one full category grid)
- [ ] Place search: geo + text + accessibility filters
- [ ] Place detail with the accessibility tree and reviews
- [ ] Auth (JWT) + contribution (complete a record, post a review)
- [ ] Next.js frontend: search (map + list), detail, contribution, account
- [x] Public API: API keys, OpenAPI, documentation

### V1.1 — Production & quality

- [ ] Real deployment: TLS, secrets, backups, monitoring, retention
- [ ] Data quality: handicap families, category mapping, duplicate review queue, coverage metrics
- [ ] Search quality: multi-criterion AND, category filter, ranking/pagination
- [ ] E2E suite (separate repo) + screen-reader audit + fr/en UI

### Out of Scope

- Gamification (challenges, teams, points) — v2
- Real-time messaging/chat — v2
- Native mobile apps — later (API-first)
- Partner referential imports (Macif, La Poste, LocalEyes, HandiPlage) — v2
- Full moderation/back-office — minimal admin in v1

## Context

### Reconstruction (sources exhausted)

Jaccede's production code is no longer accessible (S3 backups deleted, RDS gone, Wayback unavailable). The reconstruction relies on the private repositories that still exist:

| Source | Data |
|---|---|
| `jaccede-api-v4` (Flask, 2024) | `Criterion` model (hierarchical, 7 types), `Category`, `AccessibilityValue`, `OtherInformation`, partner importers |
| `commands/translations/it/*.csv` | 233 criterion/option labels, 158 categories, 52 filters, 16 TH labels |
| `jaccede-v3/docs/api/source/places_api.rst` | **Complete** category-1 grid (4 groups, 19 criteria, options, types) |
| `apidocs/docs/categories.html` | 118 categories with FR labels |
| `jaccede-dev-tools` + `jaccede-doc` | Confirm the S3 dump (deleted); no usable data |

The exact per-category grid is not fully recoverable: category 1 is used as the universal base, extended with the vocabulary and partner mappings, and made **editable in the admin**.

### Monorepo

- **Backend**: repo root (`src/letmegetin`, `tests/`, `data/`).
- **Frontend**: `web/` (Next.js, shipped in V1).
- **E2E**: later, in a **separate repository** (same model as interview-challenger).

### Tracking

Linear: dedicated **LetMeGetIn** workspace (`letmegetin`), team **LET**; one project per milestone (V1, V1.1). Every branch/commit/PR starts with `LET-<n>`. Mapping in `.planning/LINEAR.md`.

## Constraints

- **Backend**: FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic.
- **Frontend**: Next.js (App Router) + TypeScript + Tailwind + MapLibre/OSM.
- **Database**: PostgreSQL + PostGIS (geo search), dev port **55433**.
- **Quality**: ruff, mypy, bandit, pytest + coverage, pre-commit.
- **No hard dependency on Google Places**: local seed, optional enrichment.
- **Historical data**: do not claim a 1:1 copy; keep the ideas, vocabulary and structure.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI (not Django) | Async, OpenAPI auto, author's ecosystem | — Pending |
| Next.js (not SvelteKit) | SEO/SSR, a11y ecosystem, maps | — Pending |
| PostGIS + JSONB i18n | Native geo search; simple i18n | — Pending |
| Reconstructed seed (no dump) | Only data available; editable | — Pending |
| Backend + frontend monorepo | Simplicity for now; e2e separate later | — Pending |
| Linear (team LET) at the start of branch/commit/PR | Ticket ↔ code traceability | — Shipped |
| V1 without gamification/messaging/mobile | Focus on the core | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-26 after moving to the LetMeGetIn GitHub organization*
