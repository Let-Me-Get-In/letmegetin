# State: LetMeGetIn

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-26)

**Core value:** Let anyone know in seconds whether a place is truly accessible.
**Current focus:** V1.1 — Phase 10.1 (Search pagination)

## Current Position

Ticket: LET-34 (Phase 10 — search quality)
Phase: 2 / 4 of V1.1 (Phase 10 complete; 10.1 inserted)
Plan: 10-02 (complete); next: 10.1-01 (pagination, SEARCH-03)
Status: Phase 10 complete — filters narrow with AND (SEARCH-01) and by category (SEARCH-02)
Last activity: 2026-11-06 — Phase 10 plan 10-02 complete (AND criterion filters: one indexed EXISTS per id, regression tests, contract migration note).

## Performance Metrics

- Requirements: 26 v1
- Phases: 7
- Linear tickets: LET-5..LET-12
- Plans completed: 12
- Phases complete: V1 7/7; V1.1 2/4

## Accumulated Context

### Decisions

- FastAPI + SQLAlchemy 2 async + PostGIS.
- Next.js (App Router) + TS + Tailwind + MapLibre.
- Reconstructed seed (no dump); category-1 grid as the base.
- Backend + frontend monorepo; e2e in a separate repo later.
- Linear team `LET`, tickets `LET-<n>` at the start of branch/commit/PR (`commit-msg` hook).
- GSD `branching_strategy = none` (no `gsd/phase-…` branches).
- Public repo under the `Let-Me-Get-In` GitHub organization; all public artifacts in English.
- Handicap families are reviewed data (`data/referential/families.csv`), not code: `families sync` fills only the empty rows and `families audit` is the DATA-01 gate.
- Acceslibre categories are reviewed data (`data/referential/acceslibre_categories.csv`, 260 mapped / 131 reviewed gaps): resolution is alias → exact category slug → ordered `category_mapping`, and `place.source_category` keeps the raw value for `import report` (DATA-02 gate).
- Duplicates stay soft: the importer persists its 0.60–0.90 candidate on `place.duplicate_of_id`; `duplicates merge` reuses the importer's writes (canonical_id + alias + merge log) and `duplicates reject` keeps both rows — both append a `place_review_decision` row so rejections are auditable too (DATA-03).
- Coverage (`admin coverage --format csv`) is read-only and counts each real place once (canonical rows excluded), naming unresolved categories instead of dropping them (DATA-04).
- The `category` filter resolves the slug to an id in the API layer (`CategoryRepo.get_by_slug`, 422 on miss) and filters the indexed `place.category_id`; the domain port never sees a slug (SEARCH-02).
- Multiple criterion filters combine with AND: one `EXISTS` per distinct id (`dict.fromkeys`) instead of one `criterion_id IN (...)`, so each added id narrows. The change is published in `docs/public-api.md` and the OpenAPI description, because third parties that relied on the old union are affected (SEARCH-01).

### Pending Todos

- Curate the vocabulary beyond the import: promote entries and translate labels (en/es/de) by hand.

### Blockers/Concerns

- The exact per-category grid is not recoverable; base + extension + admin.

## Session Continuity

Last session: 2026-11-06
Stopped at: Completed 10-02-PLAN.md (SEARCH-01 AND criterion filters); phase 10 complete, next is 10.1-01 (SEARCH-03 pagination)
Resume file: .planning/phases/10-search-quality/10-02-SUMMARY.md

## Known debt

- **Test isolation**: the integration tests assume the dev `place` table holds
  only their fixtures. The national AccesLibre load (634 931 places, 6 Nov 2026)
  now lives in that same database, so five search tests fail locally while CI
  stays green (empty database). Fix: point the suite at a dedicated
  `letmegetin_test` database. Decided, not done.
