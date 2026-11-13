# Roadmap: LetMeGetIn

## Overview

v2.0 — Federated Data & Partners: move from a single-source directory (AccesLibre, 634 961 places) to a federated referential whose data can flow in and out of every open source, with **ODbL** as the output licence (code stays **AGPL-3.0**). The licence gate ships before anything leaves the system; the one pure-frontend requirement ships early so it is visible without waiting on the federation work.

V1 (product core) and V1.1 (production, data quality, search, e2e, accessibility) are shipped; their roadmaps are archived under `.planning/milestones/V1-phases/` and `.planning/milestones/V1.1-phases/`.

## Phases

- [x] **Phase 12: Licence provenance** - Per-row source + licence, classified per destination and enforced at every exit point (completed 2026-11-13)
- [ ] **Phase 13: Documented-place visualisation** - How well documented a place is, visible without pretending an empty place is documented
- [ ] **Phase 14: Open ODbL export** - ODbL download of places, categories, criteria and answers with cumulative attribution
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
**Plans**: TBD
**UI hint**: yes

### Phase 14: Open ODbL export
**Goal**: A partner can download the whole referential as ODbL, with attribution rendered in the export.
**Depends on**: Phase 12
**Tickets**: LET-72
**Requirements**: EXP-01, EXP-02
**Success Criteria** (what must be TRUE):
  1. A partner downloads an ODbL export of places, categories, criteria and answers, each row carrying a stable id and its origin id.
  2. The export renders cumulative attribution (AccesLibre with source name and last-update date, OpenStreetMap, Overture).
  3. The API and map are documented as Produced Works alongside the export.
**Plans**: TBD

### Phase 15: AccesLibre round trip
**Goal**: Owned rows flow back to AccesLibre as a lov2 feed, and our answers push to their API idempotently.
**Depends on**: Phase 12
**Tickets**: LET-73, LET-74
**Requirements**: PART-01, PART-02
**Success Criteria** (what must be TRUE):
  1. AccesLibre receives a lov2 feed of owned rows keyed on their identifiers, with categories and criteria in their vocabulary, plus a mapping document listing every place of ours they cannot match and why.
  2. An operator pushes our answers to the AccesLibre API idempotently.
  3. Conflict rules and provenance are strong enough that a later import cannot overwrite a fresher community contribution.
**Plans**: TBD

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
| 13. Documented-place visualisation | LET-75 | 0/— | Not started | — |
| 14. Open ODbL export | LET-72 | 0/— | Not started | — |
| 15. AccesLibre round trip | LET-73, LET-74 | 0/— | Not started | — |
| 16. OpenStreetMap | LET-77, LET-78 | 0/— | Not started | — |
| 17. Overture | LET-70, LET-71, LET-76 | 0/— | Not started | — |

---
*Created: 2026-11-13 — milestone v2.0 (Federated Data & Partners)*
