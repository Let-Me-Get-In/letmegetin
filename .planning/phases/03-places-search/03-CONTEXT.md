# Phase 3: Places & Search - Context

**Gathered:** 2026-10-27
**Status:** Ready for planning (research-backed)

<domain>
## Phase Boundary

Places: **import, deduplicate, search and serve** the accessibility record of a place.

- Import from open datasets (no Google Places — ToS forbids storing/redistributing).
- Deduplicate aggressively (collaborative creation + multi-source import).
- Search by text, proximity and accessibility filters.
- Serve the per-category criteria grid efficiently to API consumers (form generation).

Out of scope: auth/contribution writes (Phase 5), Next.js UI (Phase 6), mobile.

</domain>

<decisions>
### Validated with the product owner (2026-10-27)
- **Place sources**: Overture + Acceslibre as primary, **OSM opt-in** per deployment.
- **Community data license**: **ODbL** (attribution + share-alike).
- **Funding**: **open data + paid service/SLA + grants/sponsorship**.

## Data sources & licensing (research-backed)

Never Google Places: the Google Maps Platform ToS forbids storing/caching Places data
and building a competing database. Legal, not just cost.

| Source | License | Role |
|---|---|---|
| **Overture Places** (~88M POIs, global) | CDLA-Permissive 2.0 + Apache-2.0 (Foursquare subset) — **no OSM data, no ODbL** | Primary global seed. Stable **GERS ID**; built by an ML conflation pipeline. |
| **Acceslibre** (French ERP accessibility, Ministère de la Transition écologique) | **Licence Ouverte / Etalab 2.0** (data), **MIT** (source) | Primary French accessibility source; has a public **API** and a documented **schema**. Reuse with attribution. |
| **OpenStreetMap** | ODbL (share-alike) | Optional complement (POIs + accessibility tags). Joining OSM makes the derived DB ODbL. |
| **Tourisme & Handicap** (Atout France) | Label referentials (public PDFs) | **Criteria ontology** (not place data). |
| **EN 17210:2021 / ISO 21542:2021** | Standards (paid docs) | Canonical **criteria ontology** for the built environment. |

Decisions:
- **Overture** as the global place seed; **Acceslibre** as the French accessibility seed.
- Do **not** duplicate Acceslibre: aggregate it, credit it, and add our community layer.
- **OSM** is opt-in per deployment (its ODbL share-alike propagates to the derived DB).
- Keep provenance on every row: `source` + `source_id` (GERS ID / acceslibre id / osm id).

## Deduplication (the core data-quality problem)

Reference: Overture's conflation pipeline (history matches → blocking → pairwise ML →
clustering/promotion) and GERS IDs. We mirror the *shape*, not the ML complexity, at first.

### 1. Provenance and identity
- `place.source`, `place.source_id`; `UNIQUE(source, source_id) WHERE source_id IS NOT NULL`.
- Import is **upsert by (source, source_id)**; re-import never creates a duplicate.
- User-created places: `source = "user"`, `source_id = NULL`.

### 2. Search-before-create (prevention — the highest-leverage layer)
- Creation requires a position; the API returns **candidate places within ~100 m** with a
  normalized-name similarity, phone/website matches and category.
- UX: "Did you mean X?" → contribute to the existing place instead of creating one.
- Endpoint: `GET /api/v1/places/candidates?lat=&lng=&name=` (rate-limited), also used by the UI
  and by importers before insert.

### 3. Matching / scoring
Candidate pairs are **blocked** spatially (geohash precision ~7 ≈ 150 m, or postal code) then
scored on:
- **name**: normalized (lowercase, accents stripped, abbreviations expanded) + `pg_trgm`
  similarity (optional embedding later);
- **address**: street + postal code;
- **website**: same registrable domain;
- **phone**: same E.164 number (strong signal);
- **category**: same/near taxonomy bucket;
- **distance**: metres.

Thresholds (tunable in config, never hard-coded in the UI):
- **≥ 0.90 → auto-merge** (or link to the canonical);
- **0.60–0.90 → review queue** (community/moderator);
- **< 0.60 → distinct place**.
Chains/brands: dedupe on (brand, location), not name alone.

### 4. Soft merge, never delete
- `place.canonical_id` (nullable) + `place_alias(place_id, name)` + `place_merge_log`.
- A duplicate becomes an **alias** of the canonical; its reviews/contributions are **moved**,
  never dropped; the merge is logged (`kept_id`, `merged_id`, `score`, `actor`, `at`) and
  reversible.
- Mirrors the old Jaccede model (`canonical_id`, `has_moved`, `merge_with_other_place`,
  `fuzzy_keys`) — the blueprint already existed.

### 5. Moderation
- Auto-merge **only** at very high confidence.
- A small "possible duplicates" queue (community proposes, admin validates).
- No hard delete; every merge is auditable.

### 6. Tests
- Deterministic fixtures (same name+geo, chain vs branch, accents, moved place) → expected
  score buckets.
- Integration tests against real PostGIS (blocking + scoring + merge + re-seed idempotency).
- A property test: importing the same source twice creates zero new rows.

## Criteria tree & serving (fix the "slow per-category form" problem)

The old API assembled the criteria tree per request from groups/criteria/options — slow and
recomputed for every form.

Decisions:
- **Precompute** the per-category grid at seed/admin time into `category_grid(category_id,
  version, tree JSONB)` (or a JSONB column on `category`). Read = one row.
- `GET /api/v1/categories/{slug}/grid` returns the precomputed tree with:
  - `ETag: W/"ref-<referential_version>"` and `Cache-Control`;
  - `If-None-Match` → `304` when unchanged.
- A global `referential_version` (row/increment) bumps on any admin edit; clients refetch only
  when it changes.
- Optional `GET /api/v1/referential?version=` returns all category grids for offline/mobile use
  (large; gzip; CDN).
- Serve a **flat criteria list + relations** (`parent_id`, `position`, `type`) for clients that
  prefer to build the tree; the precomputed tree is the default for form rendering.
- CDN caching (Cloudflare) in front of the public read API.

### Criteria ontology (complete/improve the tree)
- Adopt a **standard core**: EN 17210 / ISO 21542 sequences (signalisation/cheminements,
  accès/entrées, circulation, sanitaires, accueil/services, prévention, informations
  accessibilité), matching the **Tourisme & Handicap** common trunk.
- Keep the **Jaccede vocabulary** (182 labels) as aliases/options; map each to a standard
  criterion.
- Import the **OSM accessibility tags** as objective sub-fields: `wheelchair`, `entrance:step_count`,
  `entrance:width`, `entrance:door`, `entrance:automatic_door`, `ramp:wheelchair`,
  `wheelchair:turning_circle`, `toilets:wheelchair` (+ door width 90 cm, space 150×150,
  grab rails, accessible basin), `highway=elevator` (width/length), `parking_space:width`,
  `changing_table`, `shower:wheelchair`.
- Map the **158 categories** to Overture taxonomy + OSM tags + Acceslibre categories (a
  `category_mapping` table, editable).
- The per-category grid = standard core ∩ category + specific criteria; editable in the admin.

## Business / funding model (open source, sustainable)

The mission requires **open data**; the sustainability must come from **service + grants**, not
from locking the data.

Decisions:
- **Code**: open source. Choose **AGPL-3.0** if the goal is to keep hosted derivatives open;
  otherwise **Apache-2.0**. (Decide early; it shapes contributions.)
- **Data**: publish the community layer under **ODbL** (share-alike, attribution) or
  **CC-BY-SA 4.0**; keep source attribution (Overture CDLA, Acceslibre Etalab 2.0, OSM ODbL).
  ODbL is the honest choice for a database and prevents closed commercialization.
- **API access**: **free API key application** for everyone; rate-limited free tier.
  - **Free** for open-source / non-profit / education / public-interest projects.
  - **Paid tier** for commercial use, high volume, SLA and support (service, not data lock-in).
- **Data dump**: stays open (with attribution). The paid tier is the hosted API/SLA/support;
  because the data is open, a commercial user could self-host — so monetize convenience,
  reliability and integrations, not access.
- **Funding**: grants (NGI Zero, Mozilla, AccessibleEU, ANCT, Fondation de France, Google.org,
  AWS Open Source), sponsorship (accessibility associations, insurers, transport operators),
  donations (Open Collective / GitHub Sponsors), paid services (audits, integrations, custom
  deployments).
- **Differentiation from Acceslibre**: France-wide state data exists; LetMeGetIn is
  **international, API-first, community-driven, with a richer cross-disability criteria grid**
  and an open referential usable by any site/app. Aggregate, don't duplicate.

### Honest trade-off
"Everyone can access the data" and "commercial users pay for the data" are incompatible unless
the license is share-alike with a commercial exception you control. Recommended: **open data
(ODbL/CC-BY-SA) + free API for all + paid service/SLA + grants**. Gating the *data* would betray
the mission and is fragile given Etalab/CDLA/ODbL already permit reuse.

</decisions>

<canonical_refs>
## Canonical References

### Data sources
- Overture Places: https://docs.overturemaps.org/guides/places/ (GERS ID, conflation, CDLA/Apache).
- Acceslibre API: https://acceslibre.beta.gouv.fr/api/docs/ — data Etalab 2.0, code MIT, schema
  https://schema.data.gouv.fr/MTES-MCT/acceslibre-schema/latest.html
- OSM accessibility: https://wiki.openstreetmap.org/wiki/Key:wheelchair ,
  https://wiki.openstreetmap.org/wiki/Wheelchair_accessible_toilets ,
  https://wiki.openstreetmap.org/wiki/Key:entrance

### Standards / ontology
- EN 17210:2021 (AccessibleEU) and ISO 21542:2021.
- Tourisme & Handicap referentials: https://www.atout-france.fr/fr/tourisme-et-handicap/referentiels

### Project
- `AGENTS.md`, `.planning/REQUIREMENTS.md` (PLACE-01..05), `.planning/ROADMAP.md` (Phase 3).
- Phase 1/2 contexts (DDD layering, referential models).

</canonical_refs>

<code_context>
## Existing Code Insights

- DDD layers: `domain` → `application` → `infrastructure` → `api` (Phase 1/2).
- `place` will be a new aggregate in `domain/places/` (entity, repository port), with
  `infrastructure/persistence/models.py` + migration `0003_`.
- PostGIS `geography(Point)` + GIST index; `pg_trgm` for name similarity; geohash for blocking.
- Reuse the `category_grid` precomputation from Phase 2's admin/seed.
- The public API is versioned (`/api/v1`); add `ETag`/`Cache-Control` middleware.

</code_context>

<deferred>
## Deferred Ideas

- ML pairwise matching (start with SQL/trigram scoring; upgrade if precision is insufficient).
- Embedding-based name matching.
- Machine translation of labels.
- Full OSM sync (opt-in deployment).
- Commercial billing implementation (Phase 7).

</deferred>

---

*Phase: 03-places-search*
*Context gathered: 2026-10-27 (research-backed)*
