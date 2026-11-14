# Phase 14: Open ODbL export - Context

**Gathered:** 2026-11-14
**Status:** Ready for planning

<domain>
## Phase Boundary

A partner can download the whole referential as ODbL — places, categories, criteria, answers — with cumulative attribution rendered inside the export. The phase also builds the append-only change journal that makes incremental delivery and per-place history possible; it does not build a web UI for that history, and it does not send anything to AccesLibre, OSM or Overture (phases 15–17).

</domain>

<decisions>
## Implementation Decisions

### Format and transport
- **D-01:** The export is a **ZIP of CSV files plus a manifest**, not a single JSON file and not a paginated endpoint: `places.csv`, `categories.csv`, `criteria.csv`, `answers.csv`, `aliases.csv`, `ATTRIBUTION.txt`, `manifest.json`. — **Reversibility:** costly — partners build importers on this shape; renaming a column or file breaks every consumer, so the schema is versioned in the manifest from day one.
- **D-02:** CSV is UTF-8, comma-separated, RFC 4180 quoting, header row on every file, no BOM. `manifest.json` carries `schema_version`, `generated_at`, `referential_version`, row counts per file, excluded-row counts per source and licence, and `attribution_ref`.

### Row scope
- **D-03:** Exclusion is decided **per answer**, never per place. A place is exported if its own `source_license` allows `open_export`; each answer is exported only if its own `source_license` allows it. An answer that cannot leave is omitted and counted in the manifest, by source and licence. A place is never dropped because one of its answers is withheld. — **Reversibility:** costly — a partner who ingests a partial place cannot tell what was withheld unless the manifest says so; the per-source counts are part of the contract.
- **D-04:** Only **canonical places** are exported (`canonical_id IS NULL`), including those with zero answers. Merged places never appear as places; they appear in `aliases.csv` as `alias_id → canonical_id`, which doubles as the tombstone stream for incremental consumers.

### Attribution and dates
- **D-05:** Cumulative attribution lives in `ATTRIBUTION.txt` inside the ZIP and is repeated verbatim in `manifest.json`:
  - AccesLibre — Licence Ouverte 2.0 (Etalab), source name and the last-update date of the data we hold;
  - OpenStreetMap — ODbL, © OpenStreetMap contributors;
  - Overture — CDLA-Permissive 2.0;
  - a sentence stating that the API and the map are Produced Works under ODbL (attribution only, no share-alike obligation on them).
  There is **no per-row attribution column**: the text is identical on 1.7M answer rows and belongs in one place.
- **D-06:** Dates are **source-first**: `observed_at` when the source declares it, otherwise `retrieved_at`, and `generated_at` for the export itself. Each place and answer row carries `source`, `source_license`, `source_url` (nullable) and its date. `manifest.json` carries `generated_at` and `referential_version` so a partner can tell which state it holds.

### Change journal
- **D-07:** A new append-only table `export_event` is the single history of changes: `seq` (monotone, primary key or unique), `occurred_at`, `entity` (`place` | `place_accessibility`), `entity_id`, `op` (`insert` | `update` | `merge`), `actor`, and `payload` = **the complete row state after the write** as JSONB. Full snapshots make replay idempotent and make a place history readable without reconstructing diffs. — **Reversibility:** one-way — the journal starts empty and cannot recover writes made before it existed; anything that happened earlier is only in the baseline snapshot.
- **D-08:** Events are appended **in the same transaction as the write**, at the existing single choke points (place `add`/`update`, the merge path, and `upsert_accessibility` for accepted writes). Rejected writes stay in `place_accessibility_write`; `export_event` records what the database actually contains.
- **D-09:** The journal starts at the **first export generation**: the snapshot produced that day is the baseline, and events apply over it in `seq` order. No attempt is made to reconstruct pre-journal history. A replay is a full-row upsert by id, so applying the same event twice is harmless.
- **D-10:** The incremental file is a ZIP with the same schema, produced from `--since <seq|date>`, plus `aliases.csv`; `latest.json` published beside the snapshots points to the current snapshot, the available deltas, `last_seq` and `generated_at`. Nothing is ever deleted, so there is no deletion file.

### Access, serving and production
- **D-11:** `letmegetin-admin export odbl --out <dir> [--since ...]` writes the ZIPs; the API serves them read-only through `/api/v1/export/latest.json` and `/api/v1/export/{name}.zip` from that directory, with the existing anonymous rate limit. No Caddy change, no secrets, no per-request generation.
- **D-12:** In production the generation runs **on the host**, not in the API process: `scripts/export-odbl.sh` wraps `docker compose run --rm api letmegetin-admin export odbl` with `./scripts/with-secrets.sh`, driven by a systemd timer (weekly snapshot, daily delta) writing into the served volume. A GitHub Actions `workflow_dispatch` triggers the same script on demand; no database credential and no API secret ever enters Actions.
- **D-13:** Per-place history is exposed as `letmegetin-admin place history <slug>`: date, op, actor, and a changed-field summary computed at read time from consecutive full-row payloads. No web UI and no public endpoint in this phase.

### Freedom of movement
- **D-14:** There are no partners and no external users of this export yet. The schema may be reshaped during this phase without a compatibility layer; the only obligation is that `manifest.json` announces the shape it ships (`schema_version`).

### the agent's Discretion
- CSV column names and ordering, ZIP entry naming beyond the seven files above, whether `answers.csv` is keyed by slug or numeric id (a stable id is required; both satisfy it), and the exact wording of the ATTRIBUTION text beyond the legally required elements.
- Whether `latest.json` is generated by the CLI or by the API on read.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Licence rules and provenance (phase 12)
- `data/referential/licence_destinations.csv` — the matrix; `open_export` column is the only one this phase reads.
- `data/referential/source_licences.csv` — source → licence mapping with effective dates.
- `src/letmegetin/domain/places/licence.py` — `can_redistribute()` domain predicate and `DESTINATIONS`.
- `src/letmegetin/infrastructure/persistence/licence_repositories.py` — `redistributable_place_ids()`, `exclusion_counts()`, `excluded_ids()`; the SQL twin to reuse for bulk extraction.
- `.planning/phases/12-licence-provenance/12-CONTEXT.md` — D-13/D-14 (predicate + exclusion counts), D-02 (observed vs retrieved), D-09 (ownership).

### Public contract
- `docs/public-api.md` — the partner-facing document this phase must extend with the export, the attribution and the Produced Works statement.
- `docs/openapi.json` — generated; the new read-only endpoints must appear here.

### Data model and write paths
- `src/letmegetin/infrastructure/persistence/models.py` — `PlaceModel`, `PlaceAccessibilityModel`, `PlaceAccessibilityWriteModel`, `ContributionModel`.
- `src/letmegetin/infrastructure/persistence/repositories.py` — `upsert_accessibility()` (the single answer write path), place `add`/`update`, merge.
- `src/letmegetin/application/places/import_acceslibre.py`, `src/letmegetin/application/places/contribute.py` — the two writers that must emit events.

### Operations
- `scripts/backup.sh`, `scripts/with-secrets.sh` — the host-side pattern the export timer copies (Infisical, `docker compose run`, systemd).
- `docs/deploy.md` — how the stack and its volumes are laid out.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `can_redistribute(licence, destination, matrix)` is pure and already tested; the export must call it rather than re-implement the matrix.
- `redistributable_place_ids(destination)` and `exclusion_counts(destination)` already exist in `licence_repositories.py` — the export's place filter and its manifest counters.
- `PlaceAccessibilityWriteModel` is the established append-only journal shape; `export_event` copies its pattern (and the reviewed decision that nothing is deleted).

### Established Patterns
- Operator CLI (`letmegetin.admin`, Typer) is the only write path; a bulk export command belongs there, not behind an HTTP route that mutates.
- `referential_version` is the existing freshness marker served with `ETag`; the manifest reuses it.
- DDD layering: extraction logic in `application/`, SQL in `infrastructure/`, the matrix rule in `domain/`.

### Integration Points
- `upsert_accessibility` (repositories.py) and the place `add`/`update`/merge paths are where `export_event` rows must be appended in the same transaction.
- `src/letmegetin/api/v1/router.py` is where the two read-only export routes attach.
- `docs/public-api.md` and the OpenAPI test carry the partner-facing contract.

</code_context>

<specifics>
## Specific Ideas

- "Le plus propre et le plus solide" — the journal must be good enough to become the place-history feature, not a throwaway table scoped to exports.
- "Pour le moment nous n'avons ni partenaires ni utilisateur donc tout est encore possible et modifiable" — shape the schema for correctness now, not compatibility.
- The user explicitly asked how production publishing works and rejected a local-only CLI: the timer + `docker compose run` answer is part of the phase contract, not an afterthought.

</specifics>

<deferred>
## Deferred Ideas

- Web UI for place history (operator or public).
- Per-partner export feeds and per-partner keys with their own quotas.
- Compression or format negotiation (Parquet, GeoPackage) and a spatial export.
- Backfill of pre-journal history from `created`/`updated` (lossy, deliberately refused).
- AccesLibre/OSM/Overture destination files — phases 15–17.

**Note (W-LICENCE-HARDCODE):** the OSM and Overture attribution lines are hard-coded string literals in
`application/places/attribution.py` (OSM_ATTRIBUTION_LINE, OVERTURE_ATTRIBUTION_LINE) as a DELIBERATE,
documented exception — OSM and Overture are upstream sources not yet present in `source_licences.csv`
(they arrive in phases 16–17). When they do, these literals move into the reviewed CSV data. The
AccesLibre line is NOT hard-coded: it is read from `licences.csv` by slug `lov2`.

</deferred>

---

*Phase: 14-open-odbl-export*
*Context gathered: 2026-11-14*
