# State: LetMeGetIn

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-26)

**Core value:** Let anyone know in seconds whether a place is truly accessible.
**Current focus:** V1.1 — Phase 11 (E2E & accessibility)

## Current Position

Ticket: LET-35 (Phase 11 — next)
Phase: 3 / 4 of V1.1 (Phase 10 and 10.1 complete)
Plan: 10.1-01 (complete); next: 11 planning
Status: Phase 10.1 complete — search is totally ordered and pageable past 100 hits (SEARCH-03)
Last activity: 2026-11-06 — Phase 10.1 plan 01 complete (distance + place.id total order, `offset` capped at 10 000, `X-Has-More`, web "Voir plus").

## Performance Metrics

- Requirements: 26 v1
- Phases: 7
- Linear tickets: LET-5..LET-12
- Plans completed: 13
- Phases complete: V1 7/7; V1.1 3/4

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
- Search ordering is total: `ORDER BY distance, place.id`. Distance ties are routine (one address, several activities) and Postgres may return tied rows in any order, so `LIMIT/OFFSET` without the primary-key tie-breaker duplicates or drops rows at a page boundary (SEARCH-03).
- Pagination is `offset` (cap 10 000) plus an `X-Has-More` header, not an envelope or a cursor: the response body stays a bare JSON array for live consumers. `has_more` comes from a `limit + 1` fetch trimmed in the application layer — no COUNT over 634k rows (SEARCH-03).

### Pending Todos

- Curate the vocabulary beyond the import: promote entries and translate labels (en/es/de) by hand.

### Blockers/Concerns

- The exact per-category grid is not recoverable; base + extension + admin.

## Session Continuity

Last session: 2026-11-06
Stopped at: Completed 10.1-01-PLAN.md (SEARCH-03 pagination); phase 10.1 complete, next is Phase 11 (E2E & accessibility)
Resume file: .planning/phases/10.1-search-pagination/10.1-01-SUMMARY.md

## Known debt

- **Test isolation**: the integration tests assume the dev `place` table holds
  only their fixtures. The national AccesLibre load (634 931 places, 6 Nov 2026)
  now lives in that same database, so five search tests fail locally while CI
  stays green (empty database). Fix: point the suite at a dedicated
  `letmegetin_test` database. Decided, not done.
