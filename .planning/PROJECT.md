# LetMeGetIn

## What This Is

LetMeGetIn is the modern rewrite of **Jaccede**, the collaborative guide to places accessible to people with disabilities (2002–2024). It exposes a **normalized accessibility referential** (place categories, typed hierarchical criteria, official labels) through a **public FastAPI API**, consumed by third parties and by our own Next.js frontend.

## Core Value

Let anyone know in seconds whether a place is truly accessible — through a structured, reliable accessibility record that any site or app can consume.

## Current Milestone: v2.0 Federated Data & Partners

**Goal:** Move from a single-source directory (AccesLibre, 634 961 places) to a federated referential whose data can flow in and out of every open source, with ODbL as the output licence.

**Target features:**
- Per-row licence provenance, with a redistribution filter per destination (LET-79)
- Open ODbL export with cumulative attribution (LET-72)
- AccesLibre feed in lov2, owned rows only (LET-73), and an idempotent write-back (LET-74)
- Overture mapping, overlap measurement and volumetric import (LET-71, LET-76, LET-70)
- OSM import as the community base (LET-77) and publishing our answers back to OSM (LET-78)
- Documented-place visualisation (LET-75)

## Requirements

### Validated

- Referential (categories, typed hierarchical criteria, filters, labels), reconstructed seed, public read API — V1 phases 1–2, 7
- Place search, place detail, reviews, auth and contribution — V1 phases 3–5
- Next.js frontend, public API keys and deployment — V1 phases 6–7
- Production operations, data quality, search quality (AND filters, pagination) — V1.1 phases 8–10.1
- E2E suite, strict axe gate, fr/en UI and a documented screen-reader audit — V1.1 phase 11

### Active

- [ ] Licence provenance per place and per answer, enforced per redistribution destination
- [ ] Open ODbL export of places and accessibility answers, attribution rendered in the export
- [ ] AccesLibre round trip: a lov2 feed of owned rows, then an idempotent API write-back
- [ ] Overture as the volumetric second source, with a reviewed category mapping and a measured overlap
- [ ] OSM as the community base, and our answers published back with a documented import plan
- [ ] How well documented a place is, visible on the map without pretending empty places are documented

### Out of Scope

- Gamification (challenges, teams, points) — later
- Real-time messaging/chat — later
- Native mobile apps — later (API-first)
- Partner referential imports outside the open sources (Macif, La Poste, LocalEyes, HandiPlage) — no licence basis
- Full moderation/back-office — minimal admin CLI

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

Linear: dedicated **LetMeGetIn** workspace (`letmegetin`), team **LET**; one project per milestone (V1, V1.1, V2). Every branch/commit/PR starts with `LET-<n>`. Mapping in `.planning/LINEAR.md`.

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
| V1 without gamification/messaging/mobile | Focus on the core | ✓ Good |
| Code licence AGPL-3.0, data licence ODbL | Network-use copyleft keeps hosted forks open; ODbL makes the round trips with OSM lawful | ✓ Good |
| Licence provenance on every row before any round trip | Compatibility differs per source and per direction (lov2 ≠ ODbL) | — Pending |

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
*Last updated: 2026-11-13 when starting milestone v2.0 (Federated Data & Partners)*
