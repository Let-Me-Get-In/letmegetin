# Roadmap: LetMeGetIn

## Overview

v2.0 — Federated Data & Partners: move from a single-source directory (AccesLibre, 634 961 places) to a federated referential whose data can flow in and out of every open source, with **ODbL** as the output licence (code stays **AGPL-3.0**). The licence gate ships before anything leaves the system; the one pure-frontend requirement ships early so it is visible without waiting on the federation work.

V1 (product core) and V1.1 (production, data quality, search, e2e, accessibility) are shipped; their roadmaps are archived under `.planning/milestones/V1-phases/` and `.planning/milestones/V1.1-phases/`.

## Phases

- [x] **Phase 12: Licence provenance** - Per-row source + licence, classified per destination and enforced at every exit point (completed 2026-11-13)
- [x] **Phase 13: Documented-place visualisation** - How well documented a place is, visible without pretending an empty place is documented (completed 2026-11-14)
- [x] **Phase 14: Open ODbL export** - ODbL download of places, categories, criteria and answers with attribution listing the sources present in the export (completed 2026-11-15)
- [ ] **Phase 15: AccesLibre round trip** - lov2 feed of owned rows, then an idempotent API write-back
- [ ] **Phase 16: OpenStreetMap** - OSM import as the community base, then policy-compliant write-back
- [ ] **Phase 17: Overture** - Reviewed category mapping, measured overlap, volumetric import as the second source

## Phase Details

### Phase 12: Licence provenance
**Goal**: Every place and every answer records where it came from and under what licence, and the system enforces what can flow to which destination.
**Depends on**: V1/V1.1 foundation (Phases 1–11, shipped)
**Tickets**: LET-79
**Requirements**: LIC-01, LIC-02, LIC-03, LIC-04, LIC-05
**Success Criteria** (what must be TRUE):
  1. Every place row records the source and licence it came from, and every accessibility answer records the source that produced it.
  2. A row can be classified as redistributable to a given destination (OSM, a lov2 partner, the open export), and that rule is enforced at every point where rows leave the system.
  3. A row derived from OSM is never included in a lov2 destination.
  4. Re-importing a source never overwrites a fresher contribution or a row that came from another source.
  5. Licence rules live in reviewed data (editable via the admin/CLI or seed), not in importer code.
**Plans**: 5/5 plans complete

Plans:
- [x] 12-01-PLAN.md — Provenance schema + reviewed licence data (`licences.csv`, `licence_destinations.csv`, `source_licences.csv`) + D-04 backfill (zero NULL licences)
- [x] 12-02-PLAN.md — Write-path provenance stamping (licence resolved from `source_licence`) + detail-endpoint surfacing + public contract
- [x] 12-03-PLAN.md — Reviewed licence data admin surface: `admin licences sync|matrix|audit` + seed integration (DDD-clean)
- [x] 12-04-PLAN.md — Enforcement predicate `can_redistribute` + SQL twin + exclusion manifest + `admin licences excluded` (the rule Phases 14–17 call)
- [x] 12-05-PLAN.md — Conflict/freshness rules on the shared write path (ownership, `observed_at` NULL combos, insert-if-absent, write journal)

### Phase 13: Documented-place visualisation
**Goal**: A person can see how well documented a place is, and an undocumented place is still usable.
**Depends on**: V1/V1.1 foundation (independent of the federation work)
**Tickets**: LET-75
**Requirements**: PROD-01
**Success Criteria** (what must be TRUE):
  1. A place shows how well documented it is, on a stated threshold ladder.
  2. The ladder has an accessible legend.
  3. An undocumented place still appears in search and can be completed in place — empty is never presented as documented.
**Plans**: 3/3 plans complete
Plans:
- [x] 13-01-PLAN.md — Server-owned documentation ladder + detail contract + record page level name (PROD-01)
- [x] 13-02-PLAN.md — Opt-in search field, batched rate, card marker (dot + level name) (PROD-01)
- [x] 13-03-PLAN.md — Per-family levels, legend, empty-record banner, tokens and public docs (PROD-01)
**UI hint**: yes

### Phase 14: Open ODbL export
**Goal**: A partner can download the whole referential as ODbL, with attribution rendered in the export.
**Depends on**: Phase 12
**Tickets**: LET-72
**Requirements**: EXP-01, EXP-02
**Success Criteria** (what must be TRUE):
  1. A partner downloads an ODbL export of places, categories, criteria and answers, each row carrying a stable id and its origin id.
  2. The export renders attribution listing only the sources present in the export, with legal names read from licences.csv (AccesLibre with source name and last-update date).
  3. The API and map are documented as Produced Works alongside the export.
**Plans**: 5/5 plans complete

Plans:
- [x] 14-01-PLAN.md — Append-only `export_event` journal (with MVCC `xid` boundary) at every place-write choke point + `admin place history <slug>` (D-07, D-08, D-09, D-13)
- [x] 14-02-PLAN.md — ODbL ZIP assembly (places/categories/criteria/answers/aliases + ATTRIBUTION + manifest) + `admin export odbl --out [--delta] [--since]` + MVCC-boundary `latest.json` + retention + reviewed `attribution_text` (D-01…D-06, D-10, D-14, D-15)
- [x] 14-03-PLAN.md — Read-only export routes + `export_data` volume (D-11, D-12)
- [x] 14-04-PLAN.md — Public export docs + Produced Works statement + OpenAPI regeneration (EXP-02)
- [x] 14-05-PLAN.md — Production generation: `scripts/export-odbl.sh` wrapper (snapshot|delta) + weekly/daily systemd units + `workflow_dispatch` (D-12)

Notes:
- Delivery is snapshot + moving-watermark deltas over the MVCC boundary (`safe_seq()`): `latest.json` carries `snapshot {name, seq}`, `watermark`, `retention_floor_seq` and `deltas[]` (each `{name, from_seq, to_seq}`); `--since <snapshot_seq>` is a cumulative catch-up refused below the retention floor (D-10).
- Retention is in scope (in 14-02): `export_event` is pruned to the previous snapshot boundary and delta ZIPs older than the last snapshot are removed, inside the export flock (D-15).
- Merged places' answers are remapped onto the canonical id (not dropped) and attribution lists only present sources, both decided in the 2026-11-14 review (D-04, D-05).
- The AccesLibre import is untouched and stays atomic — the MVCC boundary removed the per-transaction event cap (D-16).

### Phase 15: AccesLibre round trip
**Goal**: Owned rows flow back to AccesLibre as a lov2 feed, and our answers push to their API idempotently.
**Depends on**: Phase 12
**Tickets**: LET-73, LET-74
**Requirements**: PART-01, PART-02
**Success Criteria** (what must be TRUE):
  1. AccesLibre receives a lov2 feed of owned rows keyed on their identifiers, with categories and criteria in their vocabulary, plus a mapping document listing every place of ours they cannot match and why.
  2. An operator pushes our answers to the AccesLibre API idempotently.
  3. Conflict rules and provenance are strong enough that a later import cannot overwrite a fresher community contribution.
**Plans**: 2/6 plans executed

Plans:
**Wave 1**
- [x] 15-01-PLAN.md — Parameterise the export destination and prove the lov2_partner licence gate + directory separation (PART-01)
- [x] 15-02-PLAN.md — Promote httpx, build the fixed-origin AccesLibre adapter + pure push decision + identifier resolver (PART-02)

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 15-03-PLAN.md — The read-only identifier probe (erp_slug + rule CSV) and its blocking live run (PART-01, PART-02)

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 15-04-PLAN.md — Project our keys into AccesLibre's vocabulary (slug-first) and emit the mapping document (PART-01)

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 15-05-PLAN.md — The outbound journal, the read-then-diff push use case + `acceslibre push`, and the A1 no-op PATCH gate (PART-02)

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 15-06-PLAN.md — The `dual` licence rows (D-01/D-02) and the contributor-terms-gated re-stamp migration (PART-01, PART-02)

### Phase 16: OpenStreetMap
**Goal**: OSM becomes the community base (import in), and our answers publish back under OSM policy.
**Depends on**: Phase 12
**Tickets**: LET-77, LET-78
**Requirements**: OSM-01, OSM-02
**Success Criteria** (what must be TRUE):
  1. An operator imports the France OSM extract's POIs as `source='osm'`, idempotently on the node/way id, mapped to our categories through reviewed tags.
  2. An operator publishes our answers to OSM, following OSM's documented import and automated-edit policy (import plan, wiki page, community discussion, per-changeset comments, bot account), once the terms-of-service consent exists.
**Plans**: TBD

### Phase 17: Overture
**Goal**: Overture becomes the volumetric second source, on evidence rather than guesswork.
**Depends on**: Phase 12
**Tickets**: LET-70, LET-71, LET-76
**Requirements**: OVT-01, OVT-02, OVT-03
**Success Criteria** (what must be TRUE):
  1. A committed CSV maps Overture `basic_category` to our category slugs, with non-visitable labels deliberately emptied and documented.
  2. The Overture × AccesLibre overlap is measured by category and reported, so the import volume is chosen on evidence.
  3. An operator imports Overture French places as `source='overture'` (GERS id as source_id), never overwriting an existing AccesLibre place, and a place with no matching category still imports.
**Plans**: TBD

## Progress

| Phase | Ticket | Plans Complete | Status | Completed |
|-------|--------|----------------|--------|-----------|
| 12. Licence provenance | LET-79 | 5/5 | Complete    | 2026-11-13 |
| 13. Documented-place visualisation | LET-75 | 3/3 | Complete    | 2026-11-14 |
| 14. Open ODbL export | LET-72 | 5/5 | Complete    | 2026-11-15 |
| 15. AccesLibre round trip | LET-73, LET-74 | 2/6 | In Progress | — |
| 16. OpenStreetMap | LET-77, LET-78 | 0/— | Not started | — |
| 17. Overture | LET-70, LET-71, LET-76 | 0/— | Not started | — |

---
*Created: 2026-11-13 — milestone v2.0 (Federated Data & Partners)*
