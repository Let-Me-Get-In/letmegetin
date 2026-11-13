---
phase: 03-places-search
plan: 01
subsystem: places
tags: [places, postgis, dedup, acceslibre, search, referential, grids]
requires:
  - "Phase 2 referential (categories, criteria, filters, is_default mapping)"
  - "PostGIS 16 container on host port 55433"
provides:
  - "place, place_alias, place_merge_log, place_accessibility tables (migration 0003)"
  - "category_mapping, category_grid, referential_version tables (migration 0003)"
  - "Place aggregate + dedup scoring (normalize_name, similar_score, classify_match)"
  - "Idempotent Acceslibre importer (local CSV/JSON export)"
  - "GET /api/v1/places, /places/candidates, /places/{slug}"
  - "GET /api/v1/categories/{slug}/grid with ETag/304"
affects:
  - "Phase 4 (reviews/contribution) writes place_accessibility values"
  - "Phase 6 UI consumes the places search + grid endpoints"
tech-stack:
  added: []
  patterns:
    - "PostGIS geography generated column from plain lat/lng"
    - "Spatial blocking (ST_DWithin 100 m) + stdlib difflib name scoring"
    - "Soft merge: canonical_id + alias + audit log, never delete"
    - "Precomputed category grid invalidated by a global referential_version"
key-files:
  created:
    - migrations/versions/0003_places.py
    - src/letmegetin/domain/places/entities.py
    - src/letmegetin/domain/places/dedup.py
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/application/places/import_acceslibre.py
    - src/letmegetin/application/places/search.py
    - src/letmegetin/application/places/get_place.py
    - src/letmegetin/application/places/candidates.py
    - src/letmegetin/api/schemas/places.py
    - src/letmegetin/api/v1/places.py
    - tests/integration/test_places_import.py
    - tests/integration/test_places_search.py
    - tests/integration/test_category_grid.py
    - tests/unit/test_places_dedup.py
  modified:
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/infrastructure/persistence/mappers.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/domain/referential/entities.py
    - src/letmegetin/domain/referential/repositories.py
    - src/letmegetin/application/referential/admin.py
    - src/letmegetin/application/referential/get_category_tree.py
    - src/letmegetin/api/deps.py
    - src/letmegetin/api/v1/router.py
    - src/letmegetin/api/v1/referential.py
    - src/letmegetin/api/schemas/referential.py
    - src/letmegetin/core/exceptions.py
    - src/letmegetin/admin.py
    - src/letmegetin/seed.py
    - README.md
    - AGENTS.md
decisions:
  - "Dedup scoring uses stdlib difflib (no rapidfuzz dependency, threat T-03-SC)"
  - "place.location is a stored generated column derived from lat/lng (no drift)"
  - "Search excludes places linked to a canonical (soft-merged duplicates)"
  - "Criterion filter = a value exists for that criterion (MVP semantic)"
  - "Admin writes bump referential_version and rebuild every grid in the same transaction"
metrics:
  duration: "~2h10"
  completed: "2026-10-27"
  tests: "84 -> 124 (all passing)"
  coverage: "94.76 % line+branch"
status: complete
---

# Phase 3 Plan 1: Places, Acceslibre import, dedup and search Summary

France-first places slice: PostGIS place aggregate, an idempotent Acceslibre importer with
soft deduplication, a public search/candidates/detail API with the four handicap families,
and versioned precomputed category grids served with ETag.

## What was built

**Task 1 — schema, import, dedup** (`e1b6a6d`)
Migration `0003` creates `place`, `place_alias`, `place_merge_log`, `place_accessibility`,
`category_mapping`, `category_grid`, `referential_version`, adds `handicap_families` /
`en17210_ref` to the referential and enables `pg_trgm`. `place.location` is a **stored
generated** `geography(Point,4326)` derived from `lat`/`lng`, indexed with GIST;
`name_normalized` gets a `gin_trgm_ops` index. The domain ships the `Place` aggregate,
`make_slug`, and `dedup.py` (`normalize_name`, `similar_score`, `classify_match` at
0.90 / 0.60 thresholds). The importer upserts by `(source, source_id)`, blocks spatially
within 100 m, scores names, then auto-links (`canonical_id` + merge log + alias) or flags
`duplicate_review`. `python -m letmegetin.admin import acceslibre --file PATH` echoes
`created/linked/review/skipped`.

**Task 2 — search, candidates, detail** (`5c9c8fb`)
`ST_DWithin` + `ST_Distance` ordering, optional `q` (trigram + ILIKE), criterion-id and
handicap-family filters, bounded `radius` (≤50 km) and `limit` (≤100). Endpoints:
`GET /api/v1/places`, `GET /api/v1/places/candidates`, `GET /api/v1/places/{slug}` (404).
The detail returns the accessibility skeleton plus `accessibility_by_family` completion.

**Task 3 — families, mapping, grids** (`c19a9ae`)
`criteria.handicap_families`, `criteria.en17210_ref` and
`accessibility_filters.handicap_families` are carried end to end and exposed in the API
schemas. CLI gains `criterion families`, `criterion edit --en17210`, `category map`. The seed
imports `data/referential/category_mapping.csv` (158 rows) and precomputes all 158 grids;
every admin write bumps `referential_version` and rebuilds the grids in the same
transaction. `GET /api/v1/categories/{slug}/grid` serves the stored tree with
`ETag: W/"ref-<version>"` and answers `304` on `If-None-Match`.

## Verification

| Check | Result |
|---|---|
| `docker compose up -d --wait db` | container healthy, port 55433 |
| `uv run alembic upgrade head` | `0003 (head)`; `downgrade 0002` → `upgrade head` replay clean |
| `admin import acceslibre` (fixture, twice) | `created=3 linked=1 review=1` then `created=0 … skipped=3` |
| `pytest tests/integration/test_places_import.py` | 2 passed (idempotency, auto link, review flag, merge log, alias) |
| `pytest tests/integration/test_places_search.py` | 9 passed (distance order, radius, `q`, criterion, family, 422, candidates, detail, 404) |
| `pytest tests/integration/test_category_grid.py` | 3 passed (ETag, 304, 404) |
| `pytest tests/unit/test_places_dedup.py` | 20 passed (normalize/similar/classify parametrized) |
| `uv run pytest --cov=letmegetin --cov-branch --cov-fail-under=85` | **124 passed, 94.76 %** |
| `uv run ruff check . && ruff format --check .` | clean |
| `uv run mypy` | clean (46 files) |
| `uv run bandit -r src -c pyproject.toml` | no issues |

## Deviations from Plan

**1. [Rule 2 - Missing critical functionality] Added `place_accessibility`**
- **Found during:** Task 1.
- **Issue:** the plan filters search by criterion ids and handicap family and serves an
  accessibility skeleton, but no table stored place/criterion values — the filters would
  have been silent no-ops.
- **Fix:** `place_accessibility(place_id, criterion_id, value JSONB)` with cascade deletes,
  read through `PlaceRepository.list_accessibility`; `PlaceDetailOut` and
  `accessibility_by_family` are computed from it.
- **Files:** migration `0003`, models, mappers, repositories, `get_place.py`, schemas.
- **Commit:** `e1b6a6d`.

**2. [Rule 3 - Blocking] `HandicapFamily` lives in `domain/referential/entities.py`**
- The plan put the literal in `domain/places/entities.py`, but Task 3 needs it on
  `Criterion`/`AccessibilityFilter`, which would make the referential depend on places.
- Fix: define `HandicapFamily` + `HANDICAP_FAMILIES` in `domain/referential/entities.py` and
  re-export from `domain/places/entities.py`. Entity fields are `list[str]` (a DB array cannot
  enforce a literal, and mypy kept the invariant list honest); the literal guards the API
  query parameter and CLI input.

**3. [Rule 1 - Design simplification] `place.location` is a generated column**
- The plan asked for a `geography(Point,4326)` column. It is now
  `GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography) STORED`, so the
  importer never writes geometry and the point cannot drift from the stored coordinates.
  Verified on PG16/PostGIS 3.4 (generated columns are indexable).

**4. [Rule 2 - Correctness] `Place.category_slug` read-only projection**
- `PlaceSummaryOut.category` needs the slug, not the id; the repository fills it through a
  `LEFT JOIN categories` on `list_near`/`get_by_slug`/`get_candidates`.

**5. [Rule 3 - Blocking] `core/exceptions.py` touched in Task 2**
- `PlaceNotFound` was not in Task 2's file list but the 404 path needs it.

**6. [Rule 3 - Blocking] Existing unit tests adapted**
- `tests/unit/test_seed.py` and `tests/unit/test_admin.py` now use fake repositories that
  cannot run PostGIS grid upserts; the grid rebuild is stubbed there (covered by the
  integration tests instead). `rebuild_category_grids` has its own fake-repository unit test.

**7. [Verification] The plan's isolated coverage gate is unsatisfiable**
- `pytest tests/unit/test_places_dedup.py --cov-fail-under=85` measures the whole
  `letmegetin` package while one test file runs (9 %). The file is run without the floor and
  the 85 % gate is enforced on the full suite, which is what CI does.

**8. [Data] `data/referential/category_mapping.csv` already existed**
- 158 rows in the exact `slug;name;overture_category;osm_tag;acceslibre_family;notes` shape;
  left unchanged and now imported by the seed.

**9. [Security] bandit B324 on the slug digest**
- `hashlib.sha1(..., usedforsecurity=False)` plus an explanatory comment: the digest only
  disambiguates public slugs, it is not a security hash.

**10. [Extra test] `tests/integration/test_category_grid.py`**
- Added beyond the plan to lock the ETag/304/404 contract of the grid endpoint.

## Threat model compliance

| Threat | Disposition | Evidence |
|---|---|---|
| T-03-01 Injection | mitigated | every query is SQLAlchemy/`text()` parameter binding; the geography point is built with `ST_MakePoint(:lng,:lat)` bound parameters; the CSV import never interpolates row values into SQL |
| T-03-02 Tampering (merge) | mitigated | soft merge only (`canonical_id`, alias, `place_merge_log`), `ON DELETE SET NULL` keeps a bad link reversible, nothing is deleted |
| T-03-03 Information disclosure | mitigated | CLI errors echo the domain message (`unsupported handicap family 'olfactif' (allowed: …)`, `not found`), never SQL or the database URL; asserted in `test_admin_cli.py` and exercised manually |
| T-03-04 DoS | mitigated (partial) | `radius` ≤ 50 000 m and `limit` ≤ 100 are mandatory, `ST_DWithin` bounds the scan; rate limiting is Phase 7 by design |
| T-03-SC New dependencies | mitigated | zero new dependencies: `difflib` for similarity, `unidecode`-free accent stripping, `geoalchemy2` already declared |

## Known stubs

| Stub | File | Reason |
|---|---|---|
| `place_accessibility` is written by tests only | migration `0003` | Phase 3 ships the *skeleton* (plan scope); contribution/review writes arrive in Phase 4 |
| `accessibility_filters.handicap_families` stays `{}` | `seed.py` | `filters.json` has no criterion link to derive families from; the column and schema are ready for the admin |
| Import is a local file only (`shortcut:` comment) | `application/places/import_acceslibre.py` | no live Acceslibre API sync; upgrade path documented in the module docstring |

## Deferred

- ML pairwise matching / embeddings for dedup (thresholds are tunable constants today).
- Overture and OSM importers (the additive `source`/`category_mapping` hooks exist).
- Rate limiting on the public search (Phase 7).
- Bulk `GET /api/v1/referential?version=` for offline/mobile (03-TREE-MAPPING §5).
