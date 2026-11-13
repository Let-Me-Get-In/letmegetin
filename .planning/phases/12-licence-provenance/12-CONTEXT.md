# Phase 12: Licence provenance - Context

**Gathered:** 2026-11-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Every place and every accessibility answer records where it came from and under
which licence, and one reviewed rule decides whether a row may leave towards a
given destination. The phase delivers the data model, the reviewed licence data,
the conflict/freshness rules on write, and the enforcement predicate used by
later export and partner work.

It does **not** build the ODbL export (Phase 14), the AccesLibre feed (Phase 15),
OSM or Overture imports (Phases 16–17), nor any new UI (Phase 13).

</domain>

<decisions>
## Implementation Decisions

### Provenance shape
- **D-01:** Provenance lives in dedicated columns, not in the `value` JSONB and
  not in a separate claims table. `place` gains `source_license`, `source_url`,
  `retrieved_at`; `place_accessibility` gains `source`, `source_license`,
  `observed_at`, `recorded_at`, `actor`. One row per (place, criterion) stays
  the model. — **Reversibility:** costly — moving these columns later means a
  migration over the whole place table (634k rows) and every reader of the
  answer shape.
- **D-02:** Two dates with two meanings: `observed_at` (what the source claims,
  nullable — AccesLibre last update, OSM `check_date`) and `recorded_at` (when we
  wrote it, default `now()`). Freshness compares `observed_at`, never the
  ingestion time.
- **D-03:** Attribution is a text `actor`: `importer:acceslibre`,
  `operator:<name>`, `user:<id>`. Uniform across imports, the CLI and
  contributions; the existing `contribution.user_id` stays where it is.
- **D-04:** The migration backfills existing rows from data already present:
  `place.source_license` from `place.source` (acceslibre → lov2), answer
  `source`/`source_license` from `value->>'source'`, `observed_at` left NULL,
  `recorded_at` = migration time. No row is left with a NULL licence.

### Licence rules as data
- **D-05:** The licence catalogue is reviewed data, not code:
  `data/referential/licences.csv` (slug, name, url, obligations) reviewed in
  git and loaded into a `licence` table by the seed. Same pattern as
  `families.csv` and `acceslibre_categories.csv`.
- **D-06:** Redistribution is an explicit matrix, `data/referential/licence_destinations.csv`
  → table `licence_destination (licence_slug, destination, allowed, note)`.
  Destinations are exactly `open_export`, `osm`, `lov2_partner`. LIC-03
  ("OSM-derived never to a lov2 destination") is a **row**, not a branch.
- **D-07:** Each row snapshots the licence resolved at write time. A
  `source → licence` correspondence (with effective date) resolves new writes;
  an existing copy keeps the licence it was taken under even if the source
  re-licenses. — **Reversibility:** one-way — once a copy has been redistributed
  under a licence, restating its terms after the fact is not possible.
- **D-08:** Operator surface mirrors the existing family commands:
  `admin licences sync` (load both CSVs after review), `admin licences matrix`
  (print the matrix), `admin licences audit` (exit 1 on an unknown licence or a
  missing matrix rule). A licence-data change bumps `referential_version`.

### Conflict and freshness
- **D-09:** A row belongs to its current source. An import may update only rows
  whose `source` equals its own. A user contribution takes ownership
  (`source = 'user'`, `actor = 'user:<id>'`), so a later re-import can never
  revert it. This is LIC-04 read literally, and it is a data rule applied by
  one shared write path, not a per-importer branch.
- **D-10:** Same-source replacement requires incoming `observed_at` ≥ current
  `observed_at`. Two NULLs compare equal, so replaying the same file stays
  idempotent; an older file is rejected as `stale` instead of silently rolling
  data back.
- **D-11:** An import may **insert** a criterion that is absent on a place owned
  by another source. Sources complement each other on missing criteria; only
  overwriting is protected.
- **D-12:** Every attempted answer write is appended to
  `place_accessibility_write` (place, criterion, incoming source/licence/value,
  `decision=accepted|rejected`, `reason=stale|other_source|not_redistributable`,
  actor, timestamp). The losing value stays visible to an operator.

### Enforcement
- **D-13:** One rule, two speeds: a pure `domain/` predicate
  (`can_redistribute(licence, destination)`) for row-level checks, and the same
  predicate pushed into SQL (`JOIN licence_destination`) for bulk extraction.
  No output path re-implements it.
- **D-14:** A non-redistributable row is excluded and **counted** (per source and
  licence) in the output manifest / import report. An output never fails because
  of one forbidden row, and `--verbose` lists the excluded ids.
- **D-15:** An unknown licence (NULL, or absent from the matrix) is **refused**
  for every destination. Fail-closed; D-04 guarantees existing rows never
  exercise that default.

### Public contract
- **D-16:** `GET /api/v1/places/{slug}` exposes `source`, `license` and
  `observed_at` on the place and on every answer, as optional additive fields.
  `docs/public-api.md` records them.
- **D-17:** The search list keeps its current contract (no provenance per
  result). Provenance stays in the detail and in the export.
- **D-18:** No provenance credit is rendered in the UI in this phase. Per-criterion
  credit belongs to the Phase 13 record work; cumulative attribution belongs to
  EXP-02 in Phase 14.

### Agent's Discretion
- Column types, index choices and the exact CSV column order.
- Whether the SQL predicate is a view or a join builder, as long as the domain
  predicate is the reference implementation.
- Shape of the manifest counters, as long as they are grouped by source/licence.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/REQUIREMENTS.md` § `v2.0 Requirements — Federated Data & Partners` — LIC-01…LIC-05, and EXP-02 for the attribution wording reuse.
- `.planning/ROADMAP.md` § `Phase 12: Licence provenance` — goal, success criteria, dependency on Phases 1–11.
- `.planning/PROJECT.md` § decisions — code AGPL-3.0, data ODbL; the licence reason is the phase's premise.
- Linear **LET-79** — the ticket this phase closes.

### Existing implementation
- `src/letmegetin/infrastructure/persistence/models.py` § `PlaceModel` (202), `PlaceAccessibilityModel` (297), `PlacePhotoModel` (331) — the photo `license` column is the precedent to follow.
- `src/letmegetin/infrastructure/persistence/repositories.py` § `upsert_accessibility` (867) — the single write path to extend.
- `src/letmegetin/domain/places/acceslibre_map.py` § `accessibility_values` (35) — where `{"value","source","key"}` is produced today.
- `src/letmegetin/application/places/contribute.py` — the user write path and its `source: "user"` value.
- `src/letmegetin/application/places/import_acceslibre.py` — `SOURCE_ACCESLIBRE` and the idempotent import contract.
- `src/letmegetin/api/schemas/places.py` — the place detail response to extend (D-16).
- `docs/public-api.md` — the published contract that must record the new fields.

### Reviewed-data pattern to copy
- `data/referential/families.csv` + `admin families sync|audit` — the exact shape D-05/D-08 must reproduce.
- `data/referential/acceslibre_categories.csv` — a second reviewed CSV loaded by the seed.
- `src/letmegetin/application/referential/admin.py` — the use cases the CLI calls.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `upsert_accessibility()` — already an idempotent `ON CONFLICT DO UPDATE`; it is the one place to add the ownership/freshness check and the write journal, so every caller inherits it.
- `PlacePhotoModel.license` — a working per-row licence field and its API exposure; copy the shape.
- `admin families sync|audit` — command structure, exit-code convention and `_run_admin` runner for the new licence commands.
- `referential_version` + category-grid invalidation — already bumped by admin writes; licence data joins it.
- `import report` — the counters and exit-1 convention for the exclusion manifest (D-14).

### Established Patterns
- Reviewed data lives in `data/referential/*.csv`, versioned in git, loaded by the seed, audited by an admin command that exits 1 on a gap.
- `domain/` stays pure: predicates and entities, no SQLAlchemy. Bulk filtering therefore needs both a domain predicate and a SQL expression.
- Nothing is deleted: merges are soft, contributions append. The write journal (D-12) follows that convention.
- Write access goes through `letmegetin.admin`; no HTTP endpoint mutates data.

### Integration Points
- `place_accessibility` model + mapper + domain entity + API schema — five files change together for D-01.
- `upsert_accessibility` is called by the AccesLibre importer and by `contribute`; both must pass source/actor/licence explicitly.
- `GET /api/v1/places/{slug}` schema and its functional tests; `docs/openapi.json` is regenerated and CI-checked.
- Seed order: licences must load before places are imported, or the first import has no licence to resolve.

</code_context>

<specifics>
## Specific Ideas

- `licence_destination` is deliberately a matrix, not computed flags: adding a destination must be a data review, not a code change.
- LIC-03's rule is the test case for the whole design: `osm × lov2_partner = false` must exist as a row and be provable from the database alone.
- The exclusion counters are part of the deliverable, not logging: an operator must be able to answer "what did we leave out, and why" without reading code.

</specifics>

<deferred>
## Deferred Ideas

- **Per-criterion provenance credit in the record UI** — Phase 13 (record work) or Phase 14 for the cumulative attribution block (EXP-02).
- **Provenance on search results** — explicitly declined (D-17); revisit only if a partner asks.
- **Storing every claim (multiple values per criterion)** — declined; single row per (place, criterion) with a write journal instead.
- **D-14 exclusion counters at the exit point (output manifest / import report)** — Phase 14. Phase 12 ships the predicate, its SQL twin and the operator query `admin licences excluded`; there is no exit path to count against until the ODbL export exists, so the counters travel with it. Recorded here rather than only inside 12-04.
- **`user → odbl` vs the lov2 partner destination** — open question for Phase 15. User contributions are stamped `odbl` (the backfill's only defensible default) and the reviewed matrix refuses `odbl × lov2_partner`; that is the LIC-03 one-way rule, which is about OSM-derived rows, not about user text. Before PART-01 ships a lov2 feed, decide whether a user contribution needs its own licence slug (or the matrix needs a source dimension) so owned rows are not silently withheld.
- **Proper legal study of the licence matrix** — accepted as a provisional posture on 2026-11-13 ("on pourra rechanger plus tard si besoin, il va falloir étudier ça correctement"). Open: the obligations of each licence, whether a permissive licence (CDLA) may feed the lov2 partner (currently refused), and the ODbL↔OSM one-way rules. The CSV is the single place to change; `admin licences sync` reloads and re-audits.

</deferred>

---

*Phase: 12-Licence provenance*
*Context gathered: 2026-11-13*
