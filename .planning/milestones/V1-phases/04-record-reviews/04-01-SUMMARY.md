---
phase: 04-record-reviews
plan: 01
subsystem: places
tags: [places, accessibility, reviews, photos, acceslibre, tree, pagination]
requires:
  - "Phase 3 places model, category_grid and Acceslibre importer"
  - "PostGIS 16 container on host port 55433"
provides:
  - "review and place_photo tables (migration 0004)"
  - "Acceslibre writer for place_accessibility and place_photo"
  - "Place detail: accessibility tree with values + filled_rate + rating/review_count/photos"
  - "GET /api/v1/places/{slug}/reviews (paginated)"
affects:
  - "Phase 5 (contribution) reuses PlaceRepository.upsert_accessibility and the review table"
  - "Phase 6 UI renders the tree, the completion rate and the reviews"
tech-stack:
  added: []
  patterns:
    - "Grid tree is copied with the recorded value injected per criterion"
    - "filled_rate counts leaf criteria (groups and options are excluded)"
    - "Import refreshes source-owned values without touching user contributions"
key-files:
  created:
    - migrations/versions/0004_reviews_photos.py
    - src/letmegetin/domain/places/acceslibre_map.py
    - src/letmegetin/application/places/list_reviews.py
    - tests/unit/test_acceslibre_map.py
    - tests/unit/test_place_detail.py
    - tests/integration/test_places_reviews.py
  modified:
    - src/letmegetin/domain/places/entities.py
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/application/places/import_acceslibre.py
    - src/letmegetin/application/places/get_place.py
    - src/letmegetin/api/schemas/places.py
    - src/letmegetin/api/v1/places.py
    - tests/integration/test_places_import.py
decisions:
  - "One Acceslibre column per base criterion; unmapped columns are ignored, never guessed"
  - "The stored value keeps its source key so a claim stays traceable"
  - "Import upserts (never deletes) accessibility values, so Phase 5 contributions survive"
  - "Reviews expose published rows only; hidden rows stay in the table for moderation"
metrics:
  duration: "~1h"
  completed: "2026-10-27"
  tests: "124 -> 142 (all passing)"
  coverage: "94.29 % line+branch"
status: complete
---

# Phase 4 Plan 1: Record & Reviews Summary

The place record is now complete for reading: the accessibility tree carries recorded values and
a completion rate, reviews are paginated, and photos come from the source with their license.

## What was built

### Accessibility writer

- `domain/places/acceslibre_map.py` maps eight Acceslibre columns onto the base criterion slugs.
- `PlaceRepository.upsert_accessibility(place_id, {slug: value})` resolves slugs to ids and
  upserts; unknown slugs are ignored (no FK error).
- The importer captures the mapped columns and writes them on create **and** on re-import, so a
  refreshed export updates values without duplicating the place.

### Detail record

- `get_place` loads the precomputed grid for the place's category and copies it with each
  node's recorded `value` (or `null`).
- `filled_rate` = filled leaf criteria / leaf criteria (groups and options excluded).
- `rating` (average published review, one decimal), `review_count`, `photos`, and the existing
  flat `accessibility` + `accessibility_by_family` are returned together.

### Reviews

- `review` table (rating 1-5 check constraint, body, author, status, timestamps).
- `GET /api/v1/places/{slug}/reviews?page=&size=` returns `{items,total,page,size}`, newest
  first, published only, 404 on an unknown place.

### Photos

- `place_photo` table with `(place_id, url)` uniqueness, credit and license.
- The importer parses a `photos` JSON list or a single `photo_url`; anything else stays empty.

## Verification

- `ruff check`, `ruff format --check`, `mypy`, `bandit`: pass.
- `pytest`: 142 passed, 94.29 % line+branch (floor 85 %).
- `alembic upgrade head` on the dev PostGIS database: `0004 (head)`.

## Deferred

- Review write path and moderation (Phase 5).
- Multi-criterion filters are still OR, and no seeded criterion carries a family (Phase 3
  warnings, untouched here).
