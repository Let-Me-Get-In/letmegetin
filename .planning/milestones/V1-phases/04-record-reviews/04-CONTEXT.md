# Phase 4: Record & Reviews (read) — Context

**Gathered:** 2026-10-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Serve a **complete, readable place record** and its **reviews**. Read-only.

- `GET /api/v1/places/{slug}` returns the place + its **accessibility tree** (groups → criteria →
  options) with recorded values, a **completion rate** (`filled_rate`) and per-family scores.
- `GET /api/v1/places/{slug}/reviews` returns paginated reviews (rating 1–5 + text).
- The Acceslibre import finally writes `place_accessibility` (the Phase 3 verifier flagged that
  nothing did), so the tree is not empty.

Out of scope: posting reviews, completing a record, auth (Phase 5); the Next.js UI (Phase 6).
</domain>

<decisions>
## Decisions

- **Tree on the detail endpoint**, not a client-side join: the response embeds the category grid
  with each criterion's recorded value (or `null`) so the UI renders a form without extra calls.
  The grid stays the single source of truth (`category_grid` from Phase 3).
- **`filled_rate`** = filled criteria / criteria present in the category grid. A criterion counts
  as filled when its value is not `null`/empty — same predicate as `accessibility_by_family`.
- **Writer = Acceslibre import.** Map the export's accessibility fields to criterion slugs with
  an explicit, testable mapping table (`acceslibre_map.py`). Unknown fields are ignored, never
  guessed. This is the smallest writer that makes PLACE-04 real; user contributions arrive in
  Phase 5 and reuse the same `place_accessibility` upsert.
- **Reviews are a new table** (`review`), no auth yet: `rating` (1–5), `body`, `author_name`,
  `status` (`published`/`hidden`), timestamps. The detail exposes `rating` (average, 1 decimal)
  and `review_count`. Write path is Phase 5 (REV-02).
- **Photos**: a `place_photo` table (`url`, `credit`, `license`) fed from the Acceslibre export
  when present; the endpoint returns `[]` otherwise. PLACE-03 asks for photos; we serve what the
  source provides and never invent one.
- **Pagination contract**: `page` (≥1, default 1) + `size` (1–100, default 20); response
  `{items, total, page, size}`. Newest first.
</decisions>

<canonical_refs>
- `.planning/REQUIREMENTS.md` — PLACE-03, PLACE-04, REV-01.
- `.planning/ROADMAP.md` — Phase 4 success criteria.
- `.planning/phases/03-places-search/03-CONTEXT.md` and `03-TREE-MAPPING.md` — place model,
  criteria groups, 4 handicap families, `category_grid` serving.
- Acceslibre schema: https://schema.data.gouv.fr/MTES-MCT/acceslibre-schema/latest.html
</canonical_refs>

<code_context>
- Phase 3 (PR #6) already ships: `PlaceModel`, `PlaceAccessibilityModel` (place_id + criterion_id
  + `value` JSONB), `PlaceRepository.list_accessibility`, `get_place` (flat values + per-family
  scores), `PlaceDetailOut`, `category_grid`.
- The importer (`application/places/import_acceslibre.py`) reads identity/address/category only and
  drops accessibility payloads.
- Migrations end at `0003_places.py`; Phase 4 adds `0004_reviews_photos.py`.
</code_context>

<deferred>
- Review moderation UI and write path (Phase 5, REV-02).
- LLM-generated accessibility summaries.
- Overture/OSM accessibility payloads (only Acceslibre is mapped now).
</deferred>

---
*Phase: 04-record-reviews*
