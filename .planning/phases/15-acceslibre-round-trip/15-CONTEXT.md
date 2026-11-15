# Phase 15: AccesLibre round trip - Context

**Gathered:** 2026-11-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Owned rows flow back to AccesLibre: a lov2 feed keyed on their identifiers, and an operator-run push
of our answers into their API that is idempotent and never overwrites a fresher contribution.

Delivered by this phase:
- A `lov2_partner` destination on the existing export path (same ZIP machinery as Phase 14, no second
  serialisation), carrying only rows we may redistribute to a lov2 destination.
- A reviewed mapping document listing every place and criterion we cannot express in their vocabulary.
- An AccesLibre API client, an operator command that pushes owned answers, and the conflict rules
  that keep a later import from clobbering them.
- The licence model change that makes contributions shippable to a lov2 destination at all.

Out of scope: obtaining the API key (a human step, `15-PARTNER-ASK.md` is the message), any UI,
scheduled delivery to them (that is an ops concern once the key exists), and the 61-criterion mapping
(see Deferred).

</domain>

<decisions>
## Implementation Decisions

### Licence of the contributions (the blocker this phase must clear)
- **D-01:** A new licence slug **`dual`** joins `data/referential/licences.csv`, meaning "lov2 **and**
  ODbL". `source_licences.csv` maps `user → dual`. `licence_destinations.csv` allows `dual` to
  `lov2_partner` **and** `open_export` (and `osm`). Rationale: today `user → odbl` and
  `odbl × lov2_partner = false`, so the lov2 feed would contain **zero** contributions and be a
  freshness mirror rather than a contribution loop. The user chose dual over flatly relicensing
  their contributions to lov2, because the open export must keep its share-alike guarantee.
  — **Reversibility:** costly — the slug is written into `source_licence` rows and baked into every
  published export manifest; changing it later means a migration plus a re-explanation to partners.
- **D-02:** The `dual` slug carries its own reviewed `attribution_text` naming both licences, and the
  attribution block lists it only when at least one `dual` row is exported (the Phase 14 D-05 rule,
  unchanged).
- **D-03:** Overture stays `cdla × lov2_partner = false`. Only `lov2` and `dual` reach a lov2
  destination. Nothing OSM-derived ever does (LIC-03 stands).

### Feed shape
- **D-04:** The feed **is** the Phase 14 export path with `destination = lov2_partner`. No new
  serializer, no new archive format: the same seven CSVs, the same manifest, the same `latest.json`.
  The only differences are the licence predicate and the archive name.
- **D-05:** Rows in the feed are keyed on the identifiers AccesLibre already knows: their ERP `slug`
  where we imported it, falling back to `origin_id`. A place with neither appears in the mapping
  document, never in the feed.
- **D-06:** Categories are expressed through the inverse of `data/referential/acceslibre_categories.csv`
  (their `activite` value). A category with no inverse row makes its places unmappable and lands in
  the mapping document.

### Criterion vocabulary
- **D-07:** The feed and the push cover **the 8 columns that carry data today** — the exact set in
  `FIELD_MAP` (`src/letmegetin/domain/places/acceslibre_map.py`), inverted. Those 8 are also the only
  criteria with values across all 634 931 imported places, so mapping more would be dead work.
- **D-08:** The other 11 answerable criteria and the remaining reference criteria are listed in the
  mapping document as "not yet expressible in the AccesLibre vocabulary", each with the reason. The
  document must never silently omit a criterion.
- **D-09:** The reviewed mapping lives in **`data/referential/`** as CSV (machine-readable, versioned,
  auditable like `families.csv` and `licences.csv`), **plus** a prose section in `docs/` telling a
  partner what to do with it. No API route serves it this phase.

### Push to their API
- **D-10:** The push is **read-then-diff**: `GET /api/erps/<slug>/` first, compare field by field,
  push only what differs. Blind PATCH was rejected — it would overwrite a correction made upstream
  after our import.
- **D-11:** When both sides hold a value for the same field, **freshness decides**. Our side's claim
  date is the answer's `recorded_at` when `observed_at` is NULL (which it always is for community
  answers), otherwise `observed_at`; their side's is the ERP-level `updated_at`. Our newer answer
  wins; their newer answer is skipped and recorded.
  *Amended 2026-11-15 (was: "reusing the Phase 12 rules verbatim, NULL = oldest"). Phase 12's
  NULL-is-oldest rule would make every community answer lose to any dated AccesLibre value, which
  defeats PART-02. Found in research; amended by the developer, not the planner.*
- **D-12:** Every attempt is journaled, accepted or skipped, with the losing value kept — the same
  shape as `place_accessibility_write`. Idempotent: a replayed run produces no write and no new
  accepted event.
- **D-13:** The client is `httpx` (already a dependency), authenticated with `Authorization: Api-Key
  <key>`, key read from settings the same way as the other secrets. **No key exists yet**, so the
  phase ships against a stub server and the first real call is a blocking human checkpoint.
- **D-14:** The push is an operator command, not a web endpoint and not a cron: `letmegetin-admin
  acceslibre push [--dry-run]`. `--dry-run` prints the diff per place and writes nothing.

### Partner ask
- **D-15:** The message asking for the API key (`.planning/phases/15-acceslibre-round-trip/15-PARTNER-ASK.md`)
  also asks for written permission to credit AccesLibre on the OpenStreetMap contributors page. Without
  it, no AccesLibre-derived row can ever go to OSM (Phase 16). Recorded here so Phase 16 knows the ask
  was made and where the answer lands.

### the agent's Discretion
- Archive naming for the partner destination (must not collide with the ODbL snapshots).
- Whether the diff is computed on the CSV values or on typed values parsed from them.
- Structure of the mapping CSV's columns, provided each row names the entity, the reason and the
  identifier when one exists.
- Rate limiting and retry/backoff on their API — no published quota exists, so a conservative default
  (serial, small pause, bounded retries) is acceptable without asking.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Partner scope and licences
- `.planning/REQUIREMENTS.md` §PART-01, §PART-02 — the two requirements this phase must satisfy
- `.planning/phases/15-acceslibre-round-trip/15-PARTNER-ASK.md` — the message sent to AccesLibre, and
  the four things we are asking for
- `data/referential/licences.csv` — the licence catalogue, `attribution_text` included
- `data/referential/licence_destinations.csv` — the destination matrix; `lov2_partner` rows are the gate
- `data/referential/source_licences.csv` — source → licence correspondence, resolved at write time
- `data/referential/acceslibre_categories.csv` — 391 `activite;category_slug;places` rows; the inverse
  is the category mapping

### Existing export machinery (reuse, do not duplicate)
- `.planning/phases/14-open-odbl-export/14-CONTEXT.md` — the export decisions D-01…D-16 this phase extends
- `src/letmegetin/application/places/export.py` — the snapshot/delta generator
- `src/letmegetin/domain/places/export_plan.py` — the pure plan, file shapes, `FREE_TEXT_COLUMNS`
- `src/letmegetin/infrastructure/persistence/export_repositories.py` — the licence-filtered streams
- `src/letmegetin/domain/places/licence.py` — `can_redistribute`, `DESTINATIONS`
- `docs/public-api.md` §ODbL export — the partner-facing contract for the archive

### Provenance and conflict rules (reuse)
- `.planning/phases/12-licence-provenance/12-CONTEXT.md` — D-09 ownership, D-10 freshness, D-12 journal
- `src/letmegetin/infrastructure/persistence/repositories.py` — `upsert_accessibility`, the one answer
  write path that already enforces ownership and freshness
- `src/letmegetin/application/places/contribute.py` — how a user answer is written and stamped

### AccesLibre side
- `src/letmegetin/domain/places/acceslibre_map.py` — `FIELD_MAP`, the 8 columns that carry data; invert it
- `src/letmegetin/application/places/import_acceslibre.py` — `_COLUMNS`, `AcceslibreRow`, `ImportReport`
- `https://acceslibre.beta.gouv.fr/api/docs/` — their API: `GET /api/erps/<slug>/`,
  `GET /api/accessibility/<id>/`, `PATCH /api/erps/<slug>/`, `Authorization: Api-Key <key>`
- `https://acceslibre.beta.gouv.fr/contact/api_key/` — where the key is requested

### Project rules
- `docs/rules/index.md` — delivery, testing, language and security rules
- `docs/rules/testing.md` — test kinds and naming; a stub-backed client test is `integration`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The export path is destination-parameterised already**: `lov2_partner` sits in `DESTINATIONS` and
  the licence filter is data, so the feed is a predicate change plus a name.
- **`can_redistribute` / `_may_leave`**: one rule, domain and SQL twin. Do not write a third copy for
  the feed; call the existing pair.
- **`upsert_accessibility`**: the only answer write path, already enforcing provenance, ownership and
  freshness. The push must go through it, not around it, so a pushed answer gets the same journal.
- **`FIELD_MAP`**: 8 entries and bijective, so the push mapping is `{slug: column}` and needs no new
  data file.

### Established Patterns
- **Reviewed data lives in CSV under `data/referential/`** with a loader, an `admin … sync` command and
  an audit that exits 1 on a gap (`families.csv`, `licences.csv`). The mapping document follows it.
- **`DomainError` fail-closed** on an unknown licence or a missing mapping row — never a silent skip.
- **Operator CLI is the only write path** (`letmegetin.admin`); the push is a CLI command for that reason.
- **Journals are append-only** with the losing value preserved (`place_accessibility_write`).

### Integration Points
- `src/letmegetin/admin.py` — new `acceslibre push` command beside `import acceslibre` and `export odbl`
- `src/letmegetin/application/places/` — a new use case module for the push, mirroring `export.py`
- `src/letmegetin/infrastructure/` — a new HTTP adapter; keep `httpx` out of the domain
- `data/referential/source_licences.csv` + `licence_destinations.csv` + `licences.csv` — the licence change
- `docs/public-api.md` — the feed's partner-facing description

</code_context>

<specifics>
## Specific Ideas

- The user's own framing: AccesLibre will probably want the API push as the counterpart for using their
  data, so the feed alone is not a complete answer to the partnership.
- `15-PARTNER-ASK.md` is written and ready to send; it asks for the key, the attribution permission,
  the reciprocity expectation, and offers our measured data-quality findings as something useful back.
- The measurement to quote if they ask: only 8 of their criteria carry values nationally, and only 4
  of the 61 fields are actually populated.

</specifics>

<deferred>
## Deferred Ideas

- **The 61-criterion mapping table** — a multi-day data project (options included), not a phase-15
  deliverable. Belongs in a data ticket once a partner confirms they want it.
- **Serving the mapping document through an API route** — no consumer yet.
- **Scheduled delivery to AccesLibre** (cron/timer) — an ops concern that only makes sense once the key
  exists; the Phase 14 timer machinery can carry it later.
- **Requesting an OSM attribution permission** is asked in `15-PARTNER-ASK.md` but the answer is a
  Phase 16 input, not phase-15 work.
- **Pushing to OSM** — Phase 16 by design.

</deferred>

---

*Phase: 15-AccesLibre round trip*
*Context gathered: 2026-11-15*
