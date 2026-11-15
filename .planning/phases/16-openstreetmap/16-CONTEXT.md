# Phase 16: OpenStreetMap - Context

**Gathered:** 2026-11-15
**Status:** Ready for planning

<domain>
## Phase Boundary

OSM becomes the community base: an operator imports the France extract's POIs, and we build — but do
not activate — the path that publishes our answers back under OSM's policy.

Delivered by this phase:
- A streaming importer for the Geofabrik France PBF extract, keyed on the OSM object type and id,
  idempotent on re-run, mapped to our categories through reviewed tags.
- Reviewed tag files in `data/referential/` covering both the category tags and the accessibility
  tags that answer our own criteria.
- The OSM licence wired into the existing licence matrix, so an OSM-derived row can never reach a
  lov2 destination.
- A changeset generator, a throttle and the policy artefacts (import plan, wiki page text, changeset
  comment template, bot account notes), tested against a fake server and **not activated**.

Out of scope: getting community approval (a social process measured in weeks, not code), running the
first real changeset, the map filter for undocumented places, and the create-a-place flow (both
ticketed separately, see Deferred).

</domain>

<decisions>
## Implementation Decisions

### Where the data comes from
- **D-01:** The source is the **Geofabrik `france-latest.osm.pbf` extract**, read in streaming. This
  adds one dependency (`osmium`) — the first new package since the project began. Reading the PBF
  in streaming is the reason the import is feasible at national scale; loading it into memory is not.
- **D-02:** The importer is **idempotent on `(source, source_id)`** where `source_id` is the OSM
  object reference (`node/123`, `way/456`), reusing the existing unique index. A re-run changes
  nothing; a changed object updates in place through the Phase 12 write path.
- **D-03:** OSM rows carry **`source='osm'`**. Nothing else about the place model changes.

  > **Amendment (2026-11-16):** D-03 is amended in exactly one respect, and no other. Two nullable
  > columns are added to `place` — `osm_version` (Integer) and `osm_tags` (JSONB) — and nothing else
  > about the place model changes. Reason: an OSM `.osmChange` `<modify>` element **replaces** the
  > target object wholesale, so the generator must hold the object's full raw tag set to emit it back
  > verbatim; without `osm_tags`, a `<modify>` would silently delete every live tag we never mapped
  > (BLOCKER 1). `osm_version` is required by the OSM API to address the object being modified. No
  > other place-model change is authorised by this amendment.

### What gets imported
- **D-04:** **All POIs in the mapped categories**, not only those carrying accessibility tags. The
  point of the phase is to have undocumented places to fill, so a bakery with no accessibility data
  is exactly what we want in the database — it is visible and contributable through the Phase 13
  work.
- **D-05:** Two reviewed files in `data/referential/`, both editable by an operator:
  - the existing `category_mapping.csv` gains the missing `osm_tag` rows (34 of 158 are filled
    today),
  - a new `osm_accessibility_tags.csv` maps OSM's accessibility tags to our criteria
    (`wheelchair`, `ramp`, `handrail`, `toilets:wheelchair`, and whatever else the review accepts).
  The tag mapping is data, never a branch in the importer — same rule as the licence matrix.
- **D-06:** A POI whose tags match no reviewed category is **skipped and counted**, never guessed.
  The import report names the top unmatched tag combinations so the mapping can grow from evidence.

### Duplicates against the other sources
- **D-07:** No external API is used for duplicate checking. The dedup machinery shipped in Phase 3 is
  source-agnostic and runs against our own database, which by then holds AccesLibre, OSM and Overture:
  100 m spatial blocking, normalised-name scoring, auto-link ≥ 0.90, review 0.75–0.90, nothing ever
  deleted.
- **D-08:** The import therefore creates **linked rows, not duplicates**: an OSM bakery that already
  exists as an AccesLibre bakery becomes a row with `canonical_id` set, its name kept as an alias, and
  the merge logged.

### Publishing back to OSM (built, not activated)
- **D-09:** The publish path is a **changeset generator**, not a live writer: it produces the
  `.osmChange` document an operator uploads, plus the per-changeset comment. Wiring an automated
  uploader is deferred until the community approves the bot.
- **D-10:** Every artefact OSM's policy asks for is authored in this phase: the import plan, the wiki
  page text, the changeset comment template, the bot-account notes, and the throttle. Without them
  the changeset generator must refuse to write (`fail-closed`).
- **D-11:** Publishing requires **terms-of-service consent** the user has explicitly granted. Absent
  that consent the publish path exists but is never invoked; the gate is a reviewed flag, not a
  runtime guess.
- **D-12:** An OSM-sourced answer is **ODbL** and therefore can never reach a `lov2_partner`
  destination. The existing matrix already refuses it; this phase adds the `osm` row to
  `source_licences.csv` and proves the refusal with a test.

### Implementation choices left to the planner
- Agent's Discretion: the PBF reader's threading/filter expression, the import report CSV columns,
  the `.osmChange` element ordering, the throttle constants (no published OSM quota exists), and the
  exact shape of the policy files.

</decisions>

<canonical_refs>
## Canonical References

- `data/referential/category_mapping.csv` — 158 rows, `osm_tag` filled for 34; the reviewed category
  bridge this phase completes.
- `data/referential/source_licences.csv` — `acceslibre→lov2`, `user→dual`; gains `osm→odbl`.
- `data/referential/licence_destinations.csv` — the matrix that already refuses `odbl` to
  `lov2_partner` (LIC-03).
- `src/letmegetin/application/places/import_acceslibre.py` — the importer shape to mirror: streaming
  rows, `classify_match`, `canonical_id`/`duplicate_of_id`, idempotent on `(source, source_id)`.
- `src/letmegetin/domain/places/dedup.py` — the scoring the OSM import reuses unchanged.
- `src/letmegetin/domain/places/licence.py` — `can_redistribute` and `DESTINATIONS`.
- `src/letmegetin/application/places/export.py` — the write path that stamps provenance (D-06/D-07 of
  Phase 12).
- `.planning/phases/15-acceslibre-round-trip/15-PARTNER-ASK.md` — the template for what a partner
  needs to see, reusable for the OSM community request.

</canonical_refs>

<existing_code_insights>
## Existing Code Insights

- The AccesLibre importer already does everything the OSM importer needs except the source format:
  streaming read, dedup classification, conditional link, provenance stamping, idempotent re-run.
  Mirroring it beats inventing a second pipeline.
- `DEFAULT_CANDIDATE_RADIUS = 100.0` in `domain/places/repositories.py` is the blocking radius; it is
  already source-agnostic.
- The national review queue measured 18 987 pairs in 0.60–0.70 before the floor was raised to 0.75 —
  importing a third source will grow it, and the operator queue is the mitigation, not a blocker.
- `place.erp_slug` exists for AccesLibre; OSM has no equivalent field and needs none — `source_id` is
  the object reference.
- The licence matrix is data, so adding OSM's row is a CSV edit plus a seed, not a code branch.

</existing_code_insights>

<specific_ideas>
## Specific Ideas

- The operator should be able to run the import and read a one-screen report: how many POIs read, how
  many mapped, how many linked, how many diverted to review, and the top unmatched tag combinations.
- The wiki page text is a real deliverable the user can paste into the OSM wiki — not a placeholder.
- The changeset comment must name the project and link the wiki page, because that is what OSM's
  automated-edit policy requires and what a reviewer will look for.

</specific_ideas>

<deferred>
## Deferred Ideas

- **Map filter "places with no criteria"** — a front feature, ticketed separately; it is how a
  visitor finds somewhere to contribute, but it is not OSM work.
- **Create a place from the map** — no creation endpoint exists today; the `candidates` endpoint is
  the preventive half. Ticketed separately.
- **Automated upload** — deferred until the community approves the bot account.
- **Overture import** — Phase 17.
- **Per-object changeset splitting by area** — a real requirement at upload time, irrelevant while the
  generator is not activated.

</deferred>
