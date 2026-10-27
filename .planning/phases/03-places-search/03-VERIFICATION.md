---
phase: 03-places-search
verified: 2026-10-27T17:13:53Z
status: passed
score: 6/6 must-haves verified
ticket: LET-8
branch: LET-8-places-search
plan: 03-01-PLAN.md
requirements:
  PLACE-01: satisfied
  PLACE-02: satisfied (mechanism)
  PLACE-03: partial - address/category/coordinates shipped; rating/photos deferred
  PLACE-04: partial - values + completion shipped; full tree/filled_rate deferred
  PLACE-05: satisfied
gates:
  ruff_check: pass
  ruff_format_check: pass
  mypy: pass
  bandit: pass
  pytest: pass (124 passed, 94.76% line+branch, floor 85%)
  alembic_current: "0003 (head)"
  pr_checks: pass (6/6)
gaps: []          # no phase-blocking gap; see warnings and deferred
warnings:
  - "Accessibility values have no production writer: the Acceslibre importer drops the accessibility payload, so `place_accessibility` is populated only by tests and `?filters=`/`?family=` return [] on a fresh import."
  - "No seeded criterion or filter carries a handicap family (0 rows in the dev DB), so `?family=` is inert until an operator runs `criterion families`."
  - "Multi-criterion `filters=` is OR (place has any listed criterion), not AND: adding criteria widens instead of narrows; only a single criterion is tested."
  - "Acceslibre category resolution only matches seeded slugs or exact `category_mapping` values; live check resolved `restaurant` but left `bibliotheque`/`musee` NULL."
  - "Whole-string difflib dedup can flag unrelated names sharing a suffix as `duplicate_review` (live: 0.70 between two different `... Vérif Cat` names); conservative (never auto-merges), but adds review noise."
  - "Import is a local CSV/JSON file only (documented shortcut); no live Acceslibre sync or incremental 'updated since'."
deferred:
  - item: "Place rating and photos on the record (PLACE-03)"
    addressed_in: "Phase 4 (rating derived from reviews); photos have no explicit roadmap slot"
    evidence: "Phase 4 success criteria: 'Reviews are paginated and readable'; PLACE-03 is also mapped to Phase 4 in REQUIREMENTS.md."
  - item: "Full accessibility tree (groups -> criteria -> options) with values and filled_rate (PLACE-04)"
    addressed_in: "Phase 4"
    evidence: "Phase 4 success criteria 1-2: 'The record returns the accessibility tree ... with values' and 'The completion rate (filled_rate) is computed'."
  - item: "Overture/OSM importers, bulk referential export, public-search rate limiting"
    addressed_in: "Later phases (Phase 7 for rate limiting)"
    evidence: "03-CONTEXT.md and 03-01-SUMMARY.md 'Deferred' section."
---

# Phase 3: Places & Search Verification Report

**Phase goal (ROADMAP):** Search places by text, proximity and accessibility filters.
**Ticket:** LET-8 · **Branch:** `LET-8-places-search` · **PR:** #6
**Verified:** 2026-10-27T17:13:53Z
**Method:** goal-backward against the real repository, the live PostGIS dev container
(`letmegetin-db`, port 55433), and the GitHub PR checks. SUMMARY.md claims were re-derived
from code, SQL and live HTTP calls, not trusted.

## Verdict

**PASSED.** The plan's six must-have truths hold, the search/import/detail/grid behavior is
exercised against real PostGIS data, and every quality gate is green. The phase goal is met
as scoped by the plan (search + import + dedup + detail skeleton + versioned grids).

Three non-blocking caveats matter for the next phase: accessibility **values** and **family**
assignments have no production data path yet (tests only), multi-criterion filtering is OR,
and record `rating`/`photos` are not in this phase. See **Warnings** and **Deferred**.

## Gates

| Gate | Command | Result |
|---|---|---|
| Lint | `uv run ruff check .` | `All checks passed!` (exit 0) |
| Format | `uv run ruff format --check .` | `87 files already formatted` (exit 0) |
| Types | `uv run mypy` | `Success: no issues found in 46 source files` (exit 0) |
| Security | `uv run bandit -r src -c pyproject.toml` | 0 issues, all severities (exit 0) |
| Tests + coverage | `uv run pytest -q --cov=letmegetin --cov-branch --cov-fail-under=85` | **124 passed**, **94.76%** line+branch, floor met |
| Migration | `uv run alembic current` | `0003 (head)`; history `0001 -> 0002 -> 0003` |
| CI | `gh pr checks 6` | 6/6 `pass` (Lint, Type check, SAST, Secret detection, Unit tests, Tests + coverage) |

## Observable Truths (plan must-haves)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | A place is imported by `(source, source_id)`; re-import creates no duplicate (PLACE-05) | ✓ VERIFIED | Live: first import `created=3`, second `created=0 skipped=3`; 3 rows remain; unique partial index `place_source_source_id_uc` in `0003`. |
| 2 | Search is distance-sorted and filters by `q`, criterion ids and handicap family (PLACE-01/02) | ✓ VERIFIED | 9 live integration tests; SQL uses `ST_DWithin` + `ST_Distance` ordering, pg_trgm/ILIKE for `q`, EXISTS on `place_accessibility`/`criteria.handicap_families`. Live `?family=auditif` and `?filters=<id>` passed. |
| 3 | `GET /places/{slug}` returns address, category, coordinates and the accessibility skeleton (PLACE-03/04) | ✓ VERIFIED | `PlaceDetailOut` serializes summary + `accessibility[]` + `accessibility_by_family`; live 200/404 confirmed. Category is nullable and only resolved when the mapping matches (W4). |
| 4 | `GET /places/candidates` returns nearby fuzzy candidates | ✓ VERIFIED | Live: candidate returned at 0 m with `score=1.0`; 100 m spatial block + name scoring in use case. |
| 5 | ≥0.90 links via `canonical_id`; 0.60–0.90 flags review; nothing deleted; merge logged | ✓ VERIFIED | Live auto-link: `verify-2` → `canonical_id`, `confidence=1.0`, merge log `(kept=70, merged=71)`, alias created. Live review: score `0.868` → `operating_status=duplicate_review`, `review=1`. No DELETE/UPDATE-to-null in importer. |
| 6 | Families are data on criteria/filters; `category_grid` is precomputed and versioned | ✓ VERIFIED (data empty — W2/W3) | `criteria.handicap_families`, `criteria.en17210_ref`, `accessibility_filters.handicap_families` in `0003` + models + schemas; `criterion families`/`criterion edit --en17210` CLI + unit tests. 158 grids stored at version 40; live ETag `W/"ref-40"`, `304`, `404`. |

**Score: 6/6.** Roadmap success criteria 1–3 verified; SC4 is address+category+coordinates
only (rating deferred to Phase 4).

## Artifacts (exists → substantive → wired → data)

| Artifact | Exists | Substantive | Wired | Data | Status |
|---|---|---|---|---|---|
| `migrations/versions/0003_places.py` | ✓ | ✓ tables, indexes, generated geography, family columns | applied (`alembic current` 0003) | n/a | ✓ VERIFIED |
| `domain/places/dedup.py` | ✓ | ✓ real normalization/scoring, 0.90/0.60 thresholds | imported by importer + candidates | n/a | ✓ VERIFIED |
| `application/places/import_acceslibre.py` | ✓ | ✓ CSV/JSON parse, upsert, spatial block, score, soft link/review | CLI `import acceslibre` | places populated live | ✓ VERIFIED |
| `api/v1/places.py` | ✓ | ✓ search/candidates/detail, validated params | router included in `main.app` | real SQL against PostGIS | ✓ VERIFIED |
| `api/v1/referential.py` grid | ✓ | ✓ ETag/`304`/404 | `CategoryGridRepo` | 158 precomputed rows | ✓ VERIFIED |
| `place_accessibility` | ✓ | ✓ table + read + filters | read path only | **no production writer** (W1) | ⚠️ read-only skeleton |

## Key Links

| From | To | Via | Status |
|---|---|---|---|
| Importer | dedup service | `_candidate` + `classify_match` before insert | ✓ WIRED |
| Importer | `canonical_id` / merge log / alias | `_import_row` | ✓ WIRED |
| Search | PostGIS + pg_trgm | `ST_DWithin`/`ST_Distance`/`similarity` bound parameters | ✓ WIRED |
| Search | accessibility filters | EXISTS subqueries on `place_accessibility` + `criteria.handicap_families` | ✓ WIRED (data caveat W1) |
| Admin write | referential version + grids | `_run_admin` → `rebuild_category_grids` | ✓ WIRED (version 40, 158 rows) |

## Live Evidence (executed this verification)

All fixtures used `verify-*` source ids and were deleted afterwards; the DB was left with 0
`place` rows and a clean working tree (`git status --porcelain` empty).

| Check | Command | Result |
|---|---|---|
| Import twice (idempotency) | `python -m letmegetin.admin import acceslibre --file fixture.csv` ×2 | `created=3 linked=1 review=0 skipped=0` then `created=0 linked=0 review=0 skipped=3`; 3 rows |
| Auto-link + merge audit | SQL on `place` / `place_merge_log` / `place_alias` | `verify-2.canonical_id=70`, `confidence=1.0`; merge `(1.0, 70, 71)`; 1 alias |
| Review bucket | import a 0.868-similarity row | `operating_status=duplicate_review`, `review=1`, `confidence=0.868` |
| Soft merge is not a duplicate in search | import a 1.0-similarity pair, then `GET /places?lat=45.4&lng=5.4&radius=1000` | 1 result (canonical only); candidates returns canonical `score=1.0` |
| Search / candidates / detail | `pytest tests/integration/test_places_search.py -v` | 9 passed against real PostGIS |
| Import tests | `pytest tests/integration/test_places_import.py -v` | 2 passed |
| Grid ETag | `GET /api/v1/categories/restaurant/grid` | `200`, `ETag: W/"ref-40"`, `Cache-Control: public, max-age=300`; `If-None-Match` → `304`; unknown → `404` |
| Grid data | SQL | `category_grid=158`, `version=40` for all, `category_mapping=158` |
| Migrations | `alembic current` / `alembic history` | `0003 (head)`; `0001 -> 0002 -> 0003` |

## Requirements Coverage

| Requirement | Source plan | Status | Evidence |
|---|---|---|---|
| PLACE-01 — text + proximity search | 03-01 | ✓ SATISFIED | `GET /places?lat&lng&radius&q`; distance-sorted test + live run; radius ≤ 50 km. |
| PLACE-02 — filter by one or more criteria | 03-01 | ✓ SATISFIED (mechanism) | `filters=` + `family=` exercised live; SQL EXISTS path verified. Caveats W1/W2/W3: OR semantics for multiple ids, no production value/family data. |
| PLACE-03 — place record (address, category, rating, photos) | 03-01 | ⚠️ PARTIAL | Address, category, coordinates, accessibility skeleton returned. `rating` and `photos` absent; rating belongs to Phase 4 reviews, photos unscheduled. |
| PLACE-04 — accessibility tree with values + completion | 03-01 | ⚠️ PARTIAL | Flat `accessibility[]` + `accessibility_by_family` completion shipped; the groups→criteria→options tree and `filled_rate` are Phase 4 SC1–2. No production values yet (W1). |
| PLACE-05 — script imports a demo dataset | 03-01 | ✓ SATISFIED | Idempotent CLI import (CSV/JSON), live twice, dedup verified. No bundled demo file: an export path must be supplied. |

## Warnings (non-blocking)

1. **Accessibility-value vacuum (W1).** The importer's column map covers identity, address,
   coordinates, category, website and phone only — the Acceslibre accessibility payload is
   dropped. `place_accessibility` is written only by tests. On a fresh seed+import,
   `?filters=` and `?family=` always return `[]`, even though the SQL path is proven.
   Upgrade: extend `AcceslibreRow`/`_COLUMNS` to import values, or make Phase 4/5 the
   explicit owner.
2. **Family data empty (W2).** Live DB: 0 criteria and 0 filters carry a handicap family.
   The seed does not assign any; `?family=` is inert until `criterion families` is run.
   The CLI/use case are tested; the data is not curated.
3. **Multi-criterion semantics (W3).** `criterion_id.in_(ids)` + EXISTS = "has any of the
   selected criteria". One criterion narrows; two widen. If PLACE-02 means "all selected",
   this needs an AND (per-criterion EXISTS) and a multi-criterion test.
4. **Category mapping coverage (W4).** `resolve_slug` matches a seeded category slug or an
   exact `overture_category`/`acceslibre_family` cell. Live: `restaurant` resolved;
   `bibliotheque` and `musee` imported with `category_id NULL` (CSV uses `library`/etc.).
   Real Acceslibre category names need mapping-table coverage or an alias pass.
5. **Dedup precision (W5).** Whole-string `difflib` ratio can flag unrelated names sharing a
   suffix as `duplicate_review` (0.70 live). Auto-link uses name+distance only — the address,
   phone, website and category signals from 03-CONTEXT §3 are not used. Conservative, so no
   data loss, but review noise.
6. **Local file only (W6).** Documented `shortcut:` — no live Acceslibre API sync or
   incremental updates.

## Deferred Items

| Item | Addressed in | Evidence |
|---|---|---|
| Rating (and photos) on the record | Phase 4 (rating via reviews); photos unplanned elsewhere | Phase 4 SC3 "Reviews are paginated and readable"; PLACE-03 mapped to Phase 4 |
| Full accessibility tree + `filled_rate` (PLACE-04) | Phase 4 | Phase 4 SC1–2 |
| Overture/OSM importers, bulk referential export | Later phases | 03-CONTEXT / SUMMARY "Deferred" |
| Rate limiting on public search | Phase 7 | T-03-04 mitigation |

## Not Re-Verified (and why)

- `alembic downgrade 0002 && upgrade head` replay: destructive on the shared dev DB and not
  needed to prove the phase goal; migration 0003 is applied and its schema matches the models.
- A fresh seeded DB from zero: the current dev DB is at version 40 with 158 categories, 158
  mappings and 158 grids, which is the post-seed state; no reset was performed.

---

_Verified by the gsd-verifier subagent against the repository, live PostGIS and PR #6._
_Working tree left clean; all verification fixtures removed._
