# Phase 2: Referential & Seed - Context

**Gathered:** 2026-10-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the accessibility referential **complete and editable**:

- Curate the full criteria vocabulary (the 182 FR/IT labels) into a usable structure.
- Multilingual labels (fr/en/es/de/it) on categories, criteria and filters.
- Per-category criteria mapping (which criteria apply to which category), editable.
- A minimal **admin/CLI** to add/edit categories, criteria, options and mappings.
- The seed loader stays idempotent and Alembic-managed.

Out of scope: places/search/dedup (Phase 3), auth/contribution (Phase 5), frontend (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Referential read API (already exists)
- Phase 1 shipped the read endpoints: `GET /api/v1/categories`,
  `/categories/{slug}/criteria`, `/filters`, `/other-information`.
- Phase 2 keeps them and adds reads only where needed (e.g. a flat `GET /api/v1/criteria`
  for the admin/library view).

### Vocabulary curation
- The 182 flat labels are a **library**, not a tree. Do NOT load them as top-level
  criteria — that would pollute the category tree.
- Add a `criterion_vocabulary` table (slug, label JSONB, description JSONB) or keep
  them as an explicit "unassigned" pool; the admin promotes an entry into a
  `criteria` row (group/criterion/option) and links it to categories.
- The category-1 grid remains the canonical base tree.

### Multilingual labels
- Labels are JSONB `{fr,en,es,de,it}`. No machine translation in Phase 2; the
  admin/CLI sets them manually (a translation pass is a later task).
- The API returns the full label map; the frontend picks the locale.

### Category ↔ criteria mapping
- `category_criteria` already exists. Phase 2 adds a **default mapping** (the base
  criteria apply to every category) and per-category overrides, both editable.
- The mapping is data, not code.

### Admin
- Prefer a **Typer CLI** (`letmegetin-admin`, or `python -m letmegetin.admin`) over a
  web admin: no auth surface, no new heavy dependency, runs against the DB with the
  existing async session.
- Commands: list/add/edit category; list/add/edit criterion/option; link/unlink a
  criterion to a category; import the vocabulary; set labels.
- A web admin (`sqladmin`) is deferred until auth exists (Phase 5).

### Migrations & tests
- Any new table gets an Alembic revision (`0002_...`).
- Unit tests for the use cases (fake repositories) + integration tests for the CLI
  against the real PostGIS DB (`tests/integration/`).

</decisions>

<canonical_refs>
## Canonical References

### Project & conventions
- `AGENTS.md` — DDD layering, commands, Linear/GSD conventions.
- `.planning/REQUIREMENTS.md` — REF-01..REF-05.
- `.planning/ROADMAP.md` — Phase 2 goal and success criteria.
- `.planning/phases/01-foundation-ci/01-CONTEXT.md` — Phase 1 decisions (Alembic, CI).

### Code
- `src/letmegetin/domain/referential/` — entities + repository Protocols.
- `src/letmegetin/application/referential/` — existing use cases.
- `src/letmegetin/infrastructure/persistence/` — `*Model`s, mappers, repositories.
- `src/letmegetin/api/v1/` — existing read endpoints.
- `src/letmegetin/seed.py` — idempotent seed loader.
- `data/referential/` — generated seed (categories, criteria, filters, th, category-1 grid).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- DDD layers from Phase 1 (`domain` → `application` → `infrastructure` → `api`).
- `mappers.py` converts ORM ↔ domain entities; reuse for the admin.
- `seed.py` already upserts categories, filters, labels and the category-1 grid.

### Established Patterns
- Async SQLAlchemy 2.0 sessions (`core/db.py`), repository Protocols.
- JSONB labels; slugified stable keys.
- `alembic upgrade head` is the only schema path.

### Integration Points
- Admin/CLI uses `SessionLocal` + the repositories.
- Any new table → `0002_` migration in `migrations/versions/`.
- New reads → `api/v1/referential.py` + a use case.

</code_context>

<deferred>
## Deferred Ideas

- Machine translation (en/es/de) — later.
- Web admin (`sqladmin`) — after auth (Phase 5).
- Per-category grid curation UI (frontend) — Phase 6.
- Full partner import (Macif, La Poste…) — v2.

</deferred>

---

*Phase: 02-referential-seed*
*Context gathered: 2026-10-27*
