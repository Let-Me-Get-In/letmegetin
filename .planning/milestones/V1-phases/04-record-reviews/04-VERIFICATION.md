---
phase: 04-record-reviews
verified: 2026-10-27T22:12:00Z
status: passed
score: 6/6 must-haves verified
ticket: LET-9
branch: LET-9-record-reviews
plan: 04-01-PLAN.md
requirements:
  PLACE-03: satisfied - address, category, rating, review_count and source photos
  PLACE-04: satisfied - tree with values, filled_rate, per-family scores
  REV-01: satisfied (read) - paginated reviews and average rating
gates:
  ruff_check: pass
  ruff_format_check: pass
  mypy: pass
  bandit: pass
  pytest: pass (142 passed, 94.29% line+branch, floor 85%)
  alembic_current: "0004 (head)"
  pr_checks: pass (6/6)
gaps: []
warnings:
  - "No review writer yet: reviews are created only by tests/seed until Phase 5 (REV-02), so the average rating is null in production."
  - "No seeded criterion or filter carries a handicap family (0 rows in the dev DB), so `accessibility_by_family` stays 0 and `?family=` is inert until an operator runs `criterion families`."
  - "Multi-criterion `filters=` is OR (any listed criterion), not AND."
  - "Acceslibre category resolution still leaves `bibliotheque`/`musee` NULL; the record then has no grid, so its tree is empty and filled_rate is 0."
  - "Import remains a local CSV/JSON export only (documented shortcut)."
deferred:
  - item: "Review creation, moderation and contribution (REV-02, CONTRIB-01/02)"
    addressed_in: "Phase 5"
    evidence: "ROADMAP Phase 5: authenticated review creation and contribution logging."
  - item: "Criterion family curation and AND semantics for multi-criterion filters"
    addressed_in: "Later (admin curation, Phase 5/7)"
    evidence: "Phase 3 VERIFICATION warnings carried forward; no Phase 4 requirement covers them."
---

# Phase 4: Record & Reviews Verification Report

**Phase goal (ROADMAP):** View a complete accessibility record and its reviews.
**Ticket:** LET-9 · **Branch:** `LET-9-record-reviews` · **PR:** #8
**Verified:** 2026-10-27T22:12:00Z
**Method:** goal-backward against the code, the live PostGIS dev container (`letmegetin-db`,
port 55433), the migration chain, and the GitHub PR checks. SUMMARY claims were re-derived from
tests and SQL, not trusted.

## Requirement evidence

| Requirement | Evidence |
|---|---|
| PLACE-03 (record: address, category, rating, photos) | `PlaceDetailOut` returns address/category, `rating` (average published reviews, one decimal), `review_count` and `photos` from `place_photo`; integration test asserts 4.0/2/one photo. |
| PLACE-04 (tree with values + completion rate) | `get_place` loads `category_grid` for the place's category, injects each criterion's value, and computes `filled_rate` over leaf criteria (unit + integration tests: 0.5 and 0.0). |
| REV-01 (read reviews, rating 1-5 + text) | `GET /api/v1/places/{slug}/reviews` paginated newest-first, published only, 404 on unknown place; `review.rating` has a 1-5 check constraint. |

## Phase-3 warnings addressed

- **No `place_accessibility` writer** → the Acceslibre importer now upserts values (and photos)
  on create and re-import; unknown columns are ignored. Covered by an integration test that
  re-imports a changed export.

## Known warnings (non-blocking)

- Reviews have no write path until Phase 5, so a fresh deployment shows an empty list and a
  null rating. The read contract and table are ready.
- The family curation gap is untouched: scores are computed, but every criterion still has an
  empty `handicap_families` after seed.
