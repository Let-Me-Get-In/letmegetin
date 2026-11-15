# Phase 15: AccesLibre round trip - Research

**Researched:** 2026-11-15
**Domain:** Partner data feed (licence-gated export) + outbound idempotent write to the AccesLibre REST API (Django REST framework), inside a FastAPI / SQLAlchemy 2.0 async backend
**Confidence:** MEDIUM overall. The AccesLibre write contract is HIGH for the schema shape (live OpenAPI, fetched today) but LOW for runtime behaviour (no API key exists, so no PATCH has ever been exercised). The in-repo reuse surface is HIGH (every value quoted from source this session).

<user_constraints>
## User Constraints (from CONTEXT.md)

**Source:** `.planning/phases/15-acceslibre-round-trip/15-CONTEXT.md` (gathered 2026-11-15). Copied verbatim. The planner must honour these; research did not revisit them.

### Locked Decisions

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
- **D-04:** The feed **is** the Phase 14 export path with `destination = lov2_partner`. No new
  serializer, no new archive format: the same seven CSVs, the same manifest, the same `latest.json`.
  The only differences are the licence predicate and the archive name.
- **D-05:** Rows in the feed are keyed on the identifiers AccesLibre already knows: their ERP `slug`
  where we imported it, falling back to `origin_id`. A place with neither appears in the mapping
  document, never in the feed.
- **D-06:** Categories are expressed through the inverse of `data/referential/acceslibre_categories.csv`
  (their `activite` value). A category with no inverse row makes its places unmappable and lands in
  the mapping document.
- **D-07:** The feed and the push cover **the 8 columns that carry data today** — the exact set in
  `FIELD_MAP` (`src/letmegetin/domain/places/acceslibre_map.py`), inverted. Those 8 are also the only
  criteria with values across all 634 931 imported places, so mapping more would be dead work.
- **D-08:** The other 11 answerable criteria and the remaining reference criteria are listed in the
  mapping document as "not yet expressible in the AccesLibre vocabulary", each with the reason. The
  document must never silently omit a criterion.
- **D-09:** The reviewed mapping lives in **`data/referential/`** as CSV (machine-readable, versioned,
  auditable like `families.csv` and `licences.csv`), **plus** a prose section in `docs/` telling a
  partner what to do with it. No API route serves it this phase.
- **D-10:** The push is **read-then-diff**: `GET /api/erps/<slug>/` first, compare field by field,
  push only what differs. Blind PATCH was rejected — it would overwrite a correction made upstream
  after our import.
- **D-11:** When both sides hold a value for the same field, **freshness decides**, reusing the Phase
  12 rules verbatim (`observed_at`, NULL = oldest, user takes ownership). Our newer answer wins; their
  newer answer is skipped and recorded.
- **D-12:** Every attempt is journaled, accepted or skipped, with the losing value kept — the same
  shape as `place_accessibility_write`. Idempotent: a replayed run produces no write and no new
  accepted event.
- **D-13:** The client is `httpx` (already a dependency), authenticated with `Authorization: Api-Key
  <key>`, key read from settings the same way as the other secrets. **No key exists yet**, so the
  phase ships against a stub server and the first real call is a blocking human checkpoint.
- **D-14:** The push is an operator command, not a web endpoint and not a cron: `letmegetin-admin
  acceslibre push [--dry-run]`. `--dry-run` prints the diff per place and writes nothing.
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

### Deferred Ideas (OUT OF SCOPE)

- **The 61-criterion mapping table** — a multi-day data project (options included), not a phase-15
  deliverable. Belongs in a data ticket once a partner confirms they want it.
- **Serving the mapping document through an API route** — no consumer yet.
- **Scheduled delivery to AccesLibre** (cron/timer) — an ops concern that only makes sense once the key
  exists; the Phase 14 timer machinery can carry it later.
- **Requesting an OSM attribution permission** is asked in `15-PARTNER-ASK.md` but the answer is a
  Phase 16 input, not phase-15 work.
- **Pushing to OSM** — Phase 16 by design.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (verbatim, `.planning/REQUIREMENTS.md` lines 184–185) | Research Support |
|----|-------------|------------------|
| PART-01 | AccesLibre can receive a lov2 feed of owned rows keyed on their identifiers, with categories and criteria expressed in their vocabulary, plus a mapping document listing every place of ours they cannot match and why | Feed = Phase 14 export with a `lov2_partner` destination (§Standard Stack, §Architecture Patterns A). Blockers: `DESTINATION` is hard-coded (§Pitfall 1), ERP slug is not stored (§Pitfall 2), category inverse is one-to-many (§Pitfall 4). |
| PART-02 | An operator can push our answers to the AccesLibre API idempotently, with conflict rules and provenance strong enough that a later import cannot overwrite a fresher community contribution | Read-then-diff over `GET`/`PATCH /api/erps/<slug>/` (§AccesLibre API contract). Import-side protection already exists in `_rejection` (§Reuse surface R5). Push-side freshness has a NULL-date conflict (§Pitfall 5) and a journal-shape gap (§Pitfall 6). |
</phase_requirements>

## Summary

The CONTEXT decisions are sound, but five of their premises do not hold in the code or the live API, and the planner must resolve them before it can write executable tasks. The research did not change any locked decision; it records where a decision's stated mechanism is wrong.

1. **The export is not destination-parameterised.** CONTEXT says "The export path is destination-parameterised already". It is not: `DESTINATION = "open_export"` is a module constant read inside `_write_zip` (`src/letmegetin/application/places/export.py:61`, `:258`, `:279`, `:288-290`). The repository methods take a `destination` argument, but the use case always passes the constant. A `lov2_partner` run needs a real parameter threaded through `export_odbl` and `_write_zip`.
2. **The feed would be publicly served and would corrupt the ODbL watermark if written to the default directory.** The public route serves any `{name}.zip` in `settings.export_dir` and always serves `latest.json` from that directory (`src/letmegetin/api/v1/export.py:34`, `:41`, `:54`). A partner archive or a `latest.json` written there is exposed and overwrites the ODbL index. The partner output must go to a separate directory the route cannot reach.
3. **We do not store AccesLibre's ERP slug.** D-05 says "their ERP `slug` where we imported it". The importer maps the CSV `id`/`id_erp`/`source_id` column to our `source_id` and builds our own `slug` with `make_slug` (`src/letmegetin/application/places/import_acceslibre.py:36-37`, `:265-267`). No slug column is read. The identifier AccesLibre uses to address an ERP is therefore unknown until a keyed read-only probe confirms the mapping (§Open Question 1).
4. **The category inverse is one-to-many.** `acceslibre_categories.csv` has 391 rows over 133 distinct `category_slug` values (e.g. `doctor` appears on 30 rows). A naive inverse is ambiguous. The `places` column can break the tie.
5. **Freshness cannot be applied "verbatim" on the push side.** User writes carry `observed_at=None` (`src/letmegetin/application/places/contribute.py:39`), and Phase 12's rule treats NULL as oldest. Applied literally, every user answer would lose to any dated AccesLibre value, which inverts D-11's intent. On their side only an ERP-level `updated_at` is exposed; the per-field dates are not in the API (§Pitfall 5).

Two further corrections: **`httpx` is a dev-only dependency** (`pyproject.toml:29` sits under `[dependency-groups] dev`, not `dependencies`), so the runtime adapter needs it promoted, and **`.env.example` does not exist** in the repo.

**Primary recommendation:** Plan the phase in this order: (a) a keyed, read-only, human-gated probe that settles the identifier and the PATCH payload shape before any write code; (b) a parameterised `lov2_partner` export into a non-served directory; (c) the push use case behind an httpx adapter with a `MockTransport` integration suite; (d) the `dual` licence migration last, because it re-stamps existing contributions and needs a contributor-terms decision.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Licence gate (`can_redistribute` / SQL twin) | Domain (pure predicate) | Database (matrix rows, `_licence_allows`) | One rule, two mirrored forms, already exists; the feed and the push both call it (D-13 Phase 12). |
| lov2 feed projection (our keys → their keys, categories and criteria inverted) | Application (use case) | Domain (pure inverse maps) | Pure transformation over `PlaceRow` / `AnswerRow`; no ORM, no HTTP. |
| Feed serialisation and ZIP writing | Application (`export.py`) | Domain (`export_plan.py`) | Reused machinery (D-04); only the destination and the projection change. |
| Feed directory and public serving | Filesystem + API route (`api/v1/export.py`) | — | Must be kept out of the served directory (Pitfall 1). Route itself needs no change. |
| Mapping document (`every place we cannot match, and why`) | Data (`data/referential/*.csv`) | Docs (`docs/` partner prose) | D-09; versioned CSV plus a partner-facing section. |
| Push orchestration (read owned rows, diff, freshness, journal) | Application (new `application/places/push_acceslibre.py`) | Domain (pure diff and freshness decision) | Mirrors `export.py`; the decision logic is pure and unit-testable. |
| AccesLibre HTTP client | Infrastructure adapter (`infrastructure/acceslibre/…`) | — | `httpx` must stay out of `domain/` and `application/` (AGENTS.md layering). |
| Outbound journal (accepted / skipped, losing value kept) | Database (new append-only table) | Application | D-12; `place_accessibility_write` is for inbound writes and its CHECKs do not fit (Pitfall 6). |
| Operator command `letmegetin-admin acceslibre push [--dry-run]` | API / operator CLI (`admin.py`) | — | The only write path (AGENTS.md); no HTTP endpoint may mutate data. |
| Key storage and injection | Secrets manager (Infisical) via `scripts/with-secrets.sh` | Settings (`config.py`, `LETMEGETIN_*`) | AGENTS.md secrets rule; never a file on the host. |
| `dual` licence re-stamp of existing contributions | Database migration | Data (`source_licences.csv`, `licences.csv`) | Existing `place_accessibility.source_license` rows are stamped at write time and do not follow a CSV change. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | 0.28.1 (locked) | Outbound HTTP client to the AccesLibre REST API | Already in the lock; `MockTransport` gives an in-process stub with no network (verified, see below). The phase constraint is to add no new dependency (D-13). |
| `typer` | existing (`pyproject.toml` dependencies) | `acceslibre push` sub-command | Mirrors `import_app` / `export_app` in `admin.py`. |
| `pydantic-settings` | existing | `LETMEGETIN_ACCESLIBRE_API_KEY` and base URL | Same `env_prefix="LETMEGETIN_"` as every other secret (`config.py:13`). |
| SQLAlchemy 2.0 async + Alembic | existing | New journal table, `dual` licence migration | Migrations live in `migrations/versions/` (latest `0013_licence_attribution_text.py`). |

**Version verification:** `uv.lock` pins `httpx` at `version = "0.28.1"` (`uv.lock:579-580`, `name = "httpx"`). The local venv runs it: `uv run --offline python -c "import httpx …"` printed `httpx 0.28.1 MockTransport 3.14.0` (this session). No `npm view` / `pip index` lookup is needed: nothing new is being installed.

**Dependency promotion (required change):** `httpx>=0.27.0` is listed only under `[dependency-groups] dev` (`pyproject.toml:26-29`, `dev = [`, `"httpx>=0.27.0",`). Production code importing `httpx` at runtime needs it in `[project] dependencies` (`pyproject.toml:7-19`). This is a move, not an addition. The lock must be regenerated with `uv lock` (never hand-edited, `docs/rules/agents.md`).

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` / `pytest-asyncio` | dev group | Test runner | Already configured: `asyncio_mode = "auto"`, markers `unit` / `integration` / `functional` (`pyproject.toml`, `[tool.pytest.ini_options]`). |
| `fakeredis` | dev group | Existing | Not needed for this phase. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `httpx.MockTransport` (in-process stub) | `pytest-httpserver` / `respx` | Both are new dev dependencies. D-13 says "stub server"; `MockTransport` is in httpx itself, so no new package is needed. Use it unless a real socket is required. |
| httpx built-in `retries=` | Hand-written bounded retry loop | httpx's transport `retries` covers connection errors only, not HTTP 429. A small explicit loop that honours `Retry-After` is needed (`Retry-After` is unverified; see A4). |
| Blind PATCH | Read-then-diff (D-10) | Locked. Blind PATCH is rejected. |

**Installation (after promotion only):**
```bash
uv lock          # regenerate uv.lock after moving httpx to [project] dependencies
uv sync
```

## Package Legitimacy Audit

**No new external package is introduced by this phase.** `httpx` is already locked (`uv.lock:579-580`); its only change is a dependency-group move.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `httpx` | PyPI | established (encode/httpx, years) | not measured this session | github.com/encode/httpx | not run through `package-legitimacy check` (already locked, no install) | Approved as existing dependency; move from dev to runtime only |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.
**Honest note:** the `gsd_run query package-legitimacy check` seam was not executed because no package is being added. If the planner adds `respx` or `pytest-httpserver` for the stub, the seam must be run first.

## Architecture Patterns

### Pattern A — the lov2 feed: the same export pipeline, a different destination and projection

```
letmegetin-admin export odbl --destination lov2_partner --out <PARTNER_DIR>
        │  (destination threaded as a parameter; DESTINATION constant removed)
        ▼
application/places/export.py :: export_odbl(destination=…)
        │  stream_canonical_places(dest) / stream_answers(dest) / list_categories / list_criteria
        ▼
infrastructure/.../export_repositories.py  ── _licence_allows(col, dest)  (SQL twin of can_redistribute)
        │  PlaceRow, AnswerRow (ours: place slug, our criterion slugs, our category slugs)
        ▼
[NEW] projection (domain, pure): our key → ERP identifier; category → activite (canonical per category);
      criterion slug → one of the 8 API field names; rows with no identifier / no inverse → mapping document
        │
        ▼
export_plan.py serialisers (unchanged) → ZIP + manifest + ATTRIBUTION.txt
        ▼
<PARTNER_DIR>/  (NOT under settings.export_dir; not served by /api/v1/export/*)
```

Key points for the planner:
- The 7-CSV shape, the manifest, `FREE_TEXT_COLUMNS` and the attribution logic are reused as-is (D-04). But the **row content** changes: `PlaceRow.slug` is our slug, `AnswerRow.criterion_slug` is our slug, `PlaceRow.category_slug` is ours. The projection must rewrite these before serialisation. "No new serializer" (D-04) is compatible with a new projection step; it is not compatible with emitting our keys unchanged.
- Feed = full snapshot only in phase 15. The journal retention (`events.delete_up_to`, `export.py:455`) and `_prune_deltas` (`export.py:326-338`) are global to one `out` directory. A partner delta chain is not safe while an ODbL snapshot prunes the shared journal. Defer partner deltas.

### Pattern B — the push: read-then-diff, freshness decision, journal, idempotent PATCH

```
letmegetin-admin acceslibre push [--dry-run]
  → application/places/push_acceslibre.py
      1. select owned rows: answers with source='user' (and optionally acceslibre-sourced rows we changed)
         whose source_license can_redistribute(…, 'lov2_partner')           ← licence gate, fail-closed
      2. resolve identifier (ERP slug)                                        ← Open Question 1
      3. GET /api/erps/<slug>/  (httpx adapter)  → flatten accessibilite sections → typed values
      4. per field: equal → no-op | theirs empty → push | differs → freshness decision (pure)
            ours newer → PATCH {"accessibilite": {<only changed fields>}}
            theirs newer → skip, journal the losing (our) value
      5. journal every decision (append-only), serial, pause, bounded retry on 429/5xx
  → httpx adapter: https://acceslibre.beta.gouv.fr/api/erps/<slug>/ only (fixed host, see Security)
```

### Pattern C — the `dual` licence path (the only schema-level change)

Existing `place_accessibility.source_license` rows are stamped at write time from `source_licence` (`repositories.py:1078`, `:1114`, `:1127`, `_source_licence(source)`). A CSV edit only affects **new** writes. Existing `user` answers keep `odbl` and stay ineligible for `lov2_partner` unless re-stamped (Runtime State Inventory, §Pitfall 3).

### Recommended project structure (new files only)

```
src/letmegetin/
├── domain/places/acceslibre_push.py        # pure: diff, freshness decision, payload typing, inverse maps
├── domain/places/lov2_projection.py        # pure: our keys → partner keys, collision/unmappable rows
├── application/places/push_acceslibre.py   # use case, mirrors export.py
├── application/places/lov2_export.py       # thin wrapper or parameterised export (decide in planning)
├── infrastructure/acceslibre/client.py     # httpx adapter, the only module that imports httpx
├── infrastructure/persistence/push_repositories.py   # owned-row stream + journal
└── admin.py                                # acceslibre_app Typer group → push
migrations/versions/0014_*.py               # journal table; dual licence (may be 0015)
data/referential/acceslibre_mapping.csv     # D-09 mapping (columns: planner's discretion)
tests/integration/acceslibre/test_client.py # MockTransport stub
tests/unit/domain/places/test_acceslibre_push.py
tests/unit/domain/places/test_lov2_projection.py
tests/functional/places/test_acceslibre_push.py
tests/functional/places/test_lov2_export.py
```

Layering: `api → application → domain ← infrastructure` (AGENTS.md). The HTTP client is an infrastructure adapter behind a port that the application depends on; the domain never sees `httpx`.

### Anti-patterns to avoid
- **Writing the partner ZIP into the default `export_dir`.** Served by the public route, and it overwrites `latest.json` (Pitfall 1).
- **Blind PATCH** of the 8 fields. Rejected by D-10.
- **Sending `user_id`.** The stored user value is `{"value": …, "source": "user", "user_id": …}` (`contribute.py:33`). Only `value` may leave.
- **Coercing unknown values.** `NullBooleanField` maps any unrecognised input to `None` (see §AccesLibre API contract, Business rules), which the API then treats as a deletion. Validate types before PATCH.
- **Reusing `upsert_accessibility` to journal a push.** The push writes to AccesLibre, not to our `place_accessibility` (Pitfall 6).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP transport, TLS, timeouts | A raw socket or `urllib` client | `httpx` (locked) with explicit `timeout=` and default `verify=True` | Bounded timeouts and certificate checking are already correct; disabling `verify` is forbidden (Security V6). |
| Licence allow/deny | A new `if licence == …` branch in the feed or push | `can_redistribute` plus the existing SQL twin `_licence_allows` (`export_repositories.py:64-78`) | LIC-03 is data, not code (`licence.py` docstring). A third copy drifts. |
| Freshness comparison | A new date-compare rule in the push | Extract the Phase 12 `_rejection` logic (`repositories.py:392-411`) into a domain function both paths call | Keeps one rule. Do not import an infrastructure private function into the application layer. |
| ZIP, CSV, manifest, attribution | New serialisers | `export_plan.py` serialisers and `_write_zip` (D-04) | Already tested for formula-injection guard, manifest, attribution. |
| Retry with `Retry-After` | httpx `retries=` alone | A bounded explicit loop on 429/5xx | httpx transport retries do not cover HTTP status codes. Keep it to a small loop; no backoff library. |
| Identifier resolution | Guessing that our `origin_id` equals the AccesLibre slug | A verified mapping (Open Question 1) | The importer never stores the slug (Pitfall 2). |
| Inverse category map | `dict(zip(...))` over the CSV | An explicit canonical-per-category rule (max `places`) and a test that asserts every `category_slug` resolves | 133 categories over 391 rows is not a bijection (Pitfall 4). |

**Key insight:** the phase is almost entirely reuse. The only net-new logic is the projection (our keys → theirs), the freshness decision for the push, and the HTTP adapter. Anything beyond those three is a re-implementation of something already in `export.py`, `repositories.py` or `licence.py`.

## Runtime State Inventory

> This phase is a licence and data migration (contributions change licence) plus an outbound write. Each category answered explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `place_accessibility` rows with `source='user'` and `source_license='odbl'`: every existing contribution is stamped at write time (`repositories.py:1114`, `:1127`; `contribute.py:33-38`). Their number is unknown (no DB query run this session). | **Data migration**: re-stamp `user` rows to `dual` only after a contributor-terms decision (Pitfall 3). Code change alone affects new writes only. |
| Stored data | `place` rows with `source='acceslibre'` carry `source_license='lov2'` already (`source_licences.csv`: `acceslibre;lov2;2026-10-26`). No change. | None. These already pass `lov2 × lov2_partner = true`. |
| Stored data | `place.source_id` for AccesLibre rows = CSV `id`/`id_erp`/`source_id` (`import_acceslibre.py:36-37`). The AccesLibre ERP `slug` is **not stored anywhere**. | **Decide**: store slug via migration + re-import, or resolve by another key (Open Question 1). Do not assume. |
| Stored data | `export_event` journal: append-only, pruned by snapshot retention (`export.py:453-456`). Not partner-specific. | None for phase 15 (no partner deltas). |
| Live service config | AccesLibre side: no key exists; the PATCH target state is unknown. | Human checkpoint before any live write (D-13). |
| OS-registered state | None found: no scheduled job, timer or cron touches the export or the push in this phase (cron is deferred). | None. |
| Secrets and env vars | New variable `LETMEGETIN_ACCESLIBRE_API_KEY` (name chosen by this research; the CONTEXT does not fix it). `.env.example` **does not exist** in the repo (read attempt: "File not found"), so there is no template to extend. | Add the key to the Infisical project `39c0bbf4-…` at `prod /` (AGENTS.md); add the name to a new `.env.example` only if the team wants one. Never commit a value. |
| Build artifacts | `httpx` moves from dev to runtime dependencies. `uv.lock` must be regenerated. | `uv lock`, then `uv sync`. Never hand-edit the lock. |

**The canonical question:** *after every file is updated, what still carries the old licence?* Existing `place_accessibility` rows stamped `odbl`. The CSV change alone leaves them ineligible.

## Common Pitfalls

### Pitfall 1: the partner feed goes to the served directory and overwrites the ODbL index
**What goes wrong:** `export_odbl` writes `out/latest.json` (`export.py:446-449`) and `_prune_deltas` removes any `delta-*.zip` not listed there (`export.py:326-338`). The public route serves `settings.export_dir / "latest.json"` (`api/v1/export.py:34`) and any `{name}.zip` in `settings.export_dir` (`:54-59`).
**Why it happens:** the CONTEXT's "archive naming must not collide" addresses file names only. The collision that matters is the single `latest.json`, the shared prune and the public route.
**How to avoid:** write partner output to a directory **outside** `settings.export_dir`, passed explicitly via `--out`. Add a functional test asserting the public route returns 404 for the partner archive name and that `latest.json` is untouched after a partner run.
**Warning signs:** a partner run changes `export_dir/latest.json`; `GET /api/v1/export/<partner>.zip` returns 200.

### Pitfall 2: D-05's "their ERP slug where we imported it" is not true
**What goes wrong:** the importer never reads a slug column (`import_acceslibre.py:36-48`, `_COLUMNS`). Our `place.slug` is `make_slug(row.name, SOURCE_ACCESLIBRE, row.source_id)` (`import_acceslibre.py:265`), which is ours.
**Why it happens:** the decision assumed the importer kept AccesLibre's slug.
**How to avoid:** Open Question 1 must be closed before the feed or the push is built. Until then, the feed's identifier column is `origin_id` (= their `id`) and must be labelled as unverified in the partner document.
**Warning signs:** `places.csv` in the feed has our `slug` in the `slug` column and `origin_id` empty for AccesLibre rows.

### Pitfall 3: the `dual` change does not re-stamp existing contributions
**What goes wrong:** D-01's premise ("the lov2 feed would contain zero contributions") is fixed by adding a CSV row, but `source_licence` is `source` (PK, `models.py:424`), so there is no per-source history and `_source_licence` resolves at write time (`repositories.py:842-856`). Existing `user` rows keep `odbl` (the feed filters on the row's own `source_license`, `export_repositories.py:81-83`).
**Why it happens:** the change is data, but the stamp is a snapshot.
**How to avoid:** the planner needs (a) a migration that re-stamps `place_accessibility.source_license` from `odbl` to `dual` where `source='user'`, and (b) a decision that contributors' ODbL grant covers a `dual` re-licence. That second point is a legal and product call, not an engineering one; it should be a `checkpoint:human-verify` before the migration runs. No public contribution terms were found in `PRODUCT.md` beyond "contributions" (`PRODUCT.md:35`).
**Warning signs:** after the migration, `GET` feed shows zero `dual` answers, or a `user` answer shows `source_license='odbl'`.

### Pitfall 4: the category inverse is one-to-many
**What goes wrong:** `acceslibre_categories.csv` maps 391 `activite` values onto 133 `category_slug` values. Inverting it gives a set of `activite` per category, and `doctor` has 30 of them.
**How to avoid:** choose one canonical `activite` per category, the row with the largest `places` value (the CSV has that column), and record the choice in the mapping document. Add a unit test that every `category_slug` in the referential resolves to exactly one canonical `activite`.
**Warning signs:** the feed emits one of several `activite` values non-deterministically.

### Pitfall 5: freshness is applied with the wrong dates on both sides
**What goes wrong:**
- Our side: user writes have `observed_at=None` (`contribute.py:39`). Phase 12 `_rejection` treats NULL as oldest (`repositories.py:407-410`). Applied to the push, every user answer loses to any dated AccesLibre value. For the push, our claim date must be `recorded_at` (set to `now()` on upsert, `repositories.py:1150`), not `observed_at`.
- Their side: the API exposes no per-field date. `GET /api/erps/<slug>/` returns the ERP's `updated_at` (`updated_at:` line 2466 in the live `Erp` schema). `accessibilite` is serialised with `exclude = ("created_at", "updated_at", "completion_rate")` (upstream `api/serializers.py`), so the field-level date is not reachable.
**How to avoid:** define the push rule explicitly in planning, e.g. "theirs differs and their ERP `updated_at` is later than our `recorded_at` → skip and journal; otherwise push". State that the ERP-level date is coarse (it moves on any ERP change, not just accessibility) and that this rule can skip a value they never changed. Make this a named decision, not a silent reuse of `_rejection`.
**Warning signs:** the push skips every user answer, or pushes over a value AccesLibre corrected yesterday.

### Pitfall 6: the push journal does not fit `place_accessibility_write`
**What goes wrong:** D-12 says "the same shape as `place_accessibility_write`". That table records our inbound writes to our own DB, and its CHECKs are fixed: `decision IN ('accepted','rejected')` and `reason IS NULL OR reason IN ('stale','other_source','not_redistributable')` (`models.py:331-336`). A push needs `skipped`, a reason like `their_fresher` and `rpa_locked`, and a record of the PATCH outcome.
**How to avoid:** a new append-only `acceslibre_push_write` table (migration `0014`), with its own CHECKs. Keep the "losing value kept" column shape.
**Warning signs:** a migration that widens `place_accessibility_write` CHECKs would couple the inbound and outbound journals.

### Pitfall 7: silent deletion through type coercion
**What goes wrong:** upstream `NullBooleanField.to_internal_value` returns `None` for any value outside `TRUE_VALUES` / `FALSE_VALUES` (upstream `erp/imports/serializers.py`). The docs say the API cannot turn a `true` or `false` into `null`. Sending an unexpected string such as `"partiel"` produces `None`, which the partial update applies unless it is in `(None, "", [], ())`, and that check is on the raw input, so `"partiel"` goes through and sets the field to null.
**How to avoid:** validate each outbound value against the schema type before PATCH (booleans only from `{true,false}`, integers within 0–32767, enum membership for `entree_porte_manoeuvre`). Reject instead of coercing.
**Warning signs:** a dry-run diff shows a field going from `true` to `null`.

### Pitfall 8: the payload key is `accessibilite`, not `accessibility`
**What goes wrong:** the public docs example PATCHes `{"accessibility": {...}}` (live `/api/openapi` description). The live write schema names the nested object `accessibilite` (`ErpImport` → `accessibilite:` at line 2643), and the upstream write serializer declares `accessibilite = AccessibilityImportSerializer(many=False, required=True)`. The read side returns `accessibilite` inline (`Erp` → `accessibilite:` at line 1821), with a `url` to `/api/accessibilite/<id>/` inside it.
**How to avoid:** the first keyed probe must PATCH a non-public test field on the **staging** platform (the docs recommend staging, see the live description), and the planner must pin the key name from that result, not from the docs.
**Warning signs:** a 400 with "Veuillez fournir les données d'accessibilité." (`upstream erp/imports/serializers.py`, `validate`), meaning the nesting key is wrong.

### Pitfall 9: the 8 values have different types on read and write
**What goes wrong:** read-side booleans are typed `boolean` (e.g. `entree_pmr`, line 1317), but the write schema types them `string` nullable (line 2730). `entree_marches` and `entree_largeur_mini` are `integer` (lines 2903, 2936). `entree_porte_manoeuvre` is an enum on write (line 2889). A diff that compares the CSV string `"true"` to the JSON boolean `true` reports a false difference on every row.
**How to avoid:** normalise both sides to typed values before comparing (this is the discretion item "CSV values or typed values"; typed wins). Upstream's `TRUE_VALUES` includes both `"true"` and Python `True`, so sending JSON booleans is accepted.
**Warning signs:** the dry-run reports every mapped field as different on a place that matches.

### Pitfall 10: the stored user value leaks `user_id`
**What goes wrong:** `stored = {"value": value, "source": "user", "user_id": user.id}` (`contribute.py:33`). A payload built from the stored JSON would send `user_id` to a third party.
**How to avoid:** the push reads `value["value"]` only. Add a unit test that the outbound body contains no key other than the schema fields.

### Pitfall 11: the category translation must happen in the projection, not in SQL
**What goes wrong:** D-06 needs `activite` per place. `PlaceRow.category_slug` is our slug from `CategoryModel.slug` (`export_repositories.py:283`). The inverse map is a referential CSV, so it belongs in the projection, not in the SQL stream.
**How to avoid:** the projection takes the inverse map as an input and fails closed (mapping-document row) on a missing entry, consistent with the `DomainError` fail-closed rule in CONTEXT.

## Code Examples

Examples are **illustrative**. Values that appear in code must also appear in a verbatim quote in this document (provenance rule). Each is tagged.

### Outbound PATCH body (shape from the live schema; key name still to be confirmed)
```python
# Source: live write schema https://acceslibre.beta.gouv.fr/api/openapi (ErpImport.accessibilite, line 2643)
# Key name "accessibilite" is [VERIFIED: openapi line 2643]; the value type per field is from lines
# 2649 / 2661 / 2730 / 2736 / 2823 (string nullable), 2889 (enum), 2903 / 2936 (integer).
payload = {"accessibilite": {"entree_pmr": True}}   # JSON boolean, accepted by NullBooleanField (TRUE_VALUES contains True)
```
[VERIFIED: key `accessibilite:` at openapi line 2643; `entree_pmr:` at line 2730] [CITED: upstream `erp/imports/serializers.py` `TRUE_VALUES`] [ASSUMED: PATCH returns 200 with an ErpImport body; see A1]

### Inverse of FIELD_MAP (our slug → their field name)
```python
# Source: src/letmegetin/domain/places/acceslibre_map.py:21-30 (keys are their field names, values our slugs)
THEIR_FIELD_FOR_SLUG = {slug: field for field, slug in FIELD_MAP.items()}
assert len(THEIR_FIELD_FOR_SLUG) == len(FIELD_MAP) == 8   # bijective: 8 distinct slugs
```
[VERIFIED: acceslibre_map.py:21-30, quoted below] Bijectivity is [VERIFIED by reading the 8 values: all distinct].

### Stub client test (no network, integration kind)
```python
# Source: httpx 0.28.1 locked; MockTransport present (verified in venv this session)
import httpx

def _stub(request: httpx.Request) -> httpx.Response:
    if request.method == "GET":
        return httpx.Response(200, json={"slug": "x", "accessibilite": {"entree": {"entree_pmr": None}}})
    return httpx.Response(200, json={"slug": "x"})

client = httpx.Client(transport=httpx.MockTransport(_stub), base_url="https://acceslibre.beta.gouv.fr")
```
[VERIFIED: `httpx.MockTransport` exists in 0.28.1 (run this session)] [ASSUMED: the response body above is illustrative, not a captured AccesLibre response]

### Verbatim quotes used by the claims above
From `src/letmegetin/domain/places/acceslibre_map.py:21-30`:
```python
FIELD_MAP: dict[str, str] = {
    "entree_pmr": "entree-acces",
    "entree_largeur_mini": "entree-largeur-de-porte-cm",
    "entree_marches": "entree-obstacles-a-la-porte-d-entree",
    "entree_porte_manoeuvre": "entree-ouverture-de-porte",
    "accueil_cheminement_plain_pied": "circulation-circulation-dans-les-allees",
    "sanitaires_presence": "services-et-equipements-sanitaires",
    "stationnement_ext_pmr": "exterieur-place-gig-gic-a-proximite",
    "transport_station_presence": "exterieur-transports-accessibles-a-proximite",
}
```

From `src/letmegetin/domain/places/licence.py:15`:
```python
DESTINATIONS: tuple[str, ...] = ("open_export", "osm", "lov2_partner")
```

From `src/letmegetin/application/places/export.py:61`:
```python
DESTINATION = "open_export"
```

From `src/letmegetin/api/v1/export.py:34`, `:41`, `:54`:
```python
payload = json.loads((settings.export_dir / "latest.json").read_text(encoding="utf-8"))
...
    "/export/{name}.zip",
...
    filename = f"{name}.zip"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 14: one destination (`open_export`), one `latest.json` | Phase 15: second destination, separate output directory and watermark | this phase | Requires parameterisation and a directory split (Pitfall 1). |
| Phase 12: NULL `observed_at` = oldest, user takes ownership | Push side needs an explicit "our claim date = recorded_at" rule | this phase | A named decision, not a reused rule (Pitfall 5). |
| Public docs: `accessibility` key | Live schema: `accessibilite` key on both read and write | live today (2026-11-15) | Pin the key from the staging probe (Pitfall 8). |

**Deprecated/outdated:**
- The docs' `{"accessibility": …}` example is treated as **unverified** until the keyed probe; the live schema uses `accessibilite`.
- `FIELD_MAP` comment says "The previous keys ('acces_entree', ...) matched no column at all" (`acceslibre_map.py:17-20`). That is a historic fix, still correct.

## Assumptions Log

> Every claim tagged `[ASSUMED]` in this research. Each needs human confirmation before it becomes a locked decision.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PATCH `/api/erps/<slug>/` with `{"accessibilite": {…}}` returns 200 with an `ErpImport` body. | §Code Examples, §AccesLibre API contract | The push's success check is wrong; a 200 may hide a silent no-op. |
| A2 | Keyed `GET /api/erps/<slug>/` returns the same `accessibilite` section names as the anonymous-readable schema. | §AccesLibre API contract | The read-then-diff flattening is wrong. |
| A3 | Our `origin_id` (= CSV `id`) is **not** AccesLibre's ERP slug. | §Pitfall 2, §Open Question 1 | If it is, the identifier problem disappears; if it is a different key, every PATCH targets the wrong ERP. |
| A4 | A 429 response carries `Retry-After`. Not documented. | §Don't Hand-Roll | The backoff falls back to a fixed pause; no data risk, but a longer run. |
| A5 | No published quota: the docs state "a maximum number of requests per second is defined" with no number. | §Standard Stack | The serial-with-pause default may still exceed the limit. |
| A6 | The upstream `master` branch matches the deployed production code. The live OpenAPI corroborates the shape, not the internals. | §AccesLibre API contract | Internal behaviour (NullBoolean coercion, `_rejection`-like rules on their side) may differ. |
| A7 | `httpx.MockTransport` satisfies D-13's "stub server" intent. | §Alternatives | If a real socket is required, `pytest-httpserver` becomes a new dev dependency. |
| A8 | Sentry's httpx integration does not record `Authorization` headers as breadcrumbs. | §Security V7 | A key could appear in an error report. |
| A9 | "lov2 feed" has no inbound specification at AccesLibre; it is our own CSV bundle under `lov2_partner`. The AccesLibre schema page (`schema.data.gouv.fr/.../documentation.html`) returned 404 this session. | §Open Question 5 | The format the partner expects could differ from ours. |
| A10 | The local Postgres test database (`letmegetin_test`, port 55433) is available. Not probed this session. | §Environment Availability | Functional tests cannot run. |
| A11 | The number of existing `user` contributions (rows to re-stamp) is unknown. | §Runtime State Inventory | The migration's scope and review cost are unknown. |

**If this table is non-empty:** A1–A11 require confirmation. A3 and A1 block the phase; A1 is the first thing the keyed probe checks.

## Open Questions

1. **Which identifier does AccesLibre use for a place we imported?**
   - What we know: we store `place.source_id` = CSV `id`/`id_erp`/`source_id` (`import_acceslibre.py:36-37`); we do not store a slug. The public API accepts the slug on `GET`/`PATCH /api/erps/<slug>/`, and also a list filter `?source=…&source_id=…` (live `listErps` description: "returns a record identified by its `source` and `source_id`"), plus `?uuid=` ("Unique OpenData identifier").
   - What's unclear: whether the CSV `id` equals the ERP `uuid`, the ERP `slug`, or neither; whether our imported ERPs carry `source = "acceslibre"` on the AccesLibre side (the enum for `source` in the live spec includes `acceslibre`, but the mapping of our rows to it is unverified).
   - Recommendation: the first keyed call is a read-only probe: fetch one known `origin_id` via `?uuid=` and via `?source=acceslibre&source_id=` and compare the returned `slug` to our `place.slug`/`origin_id`. Block the feed's identifier column on the result. Do not guess.

2. **Where does the partner feed live, and who reads it?**
   - What we know: `PART-01` says "AccesLibre can receive a lov2 feed". No inbound feed endpoint or specification was found. Our public route serves files from `export_dir` (Pitfall 1), so one delivery option is to publish the partner archive on a non-ODbL path. That needs a human decision.
   - Recommendation: ask the partner in the same thread as the key. Until answered, the feed is produced and the mapping document is delivered by hand.

3. **Which rows does the push send?**
   - What we know: the push is for "our answers" (PART-02). Owned rows are the `user` answers (`dual` after migration) and possibly acceslibre-sourced values we changed (none today; the importer only writes).
   - Recommendation: push only `source='user'` rows whose licence allows `lov2_partner`. Document that acceslibre-sourced rows are never pushed (they are theirs).

4. **How is the push's freshness decided on their side?**
   - What we know: only ERP-level `updated_at` is exposed (Pitfall 5).
   - Recommendation: the coarse rule in Pitfall 5, stated explicitly, with the consequence documented.

5. **Does the lov2 feed need its own licence attribution text?**
   - What we know: D-02 requires `dual`'s own `attribution_text` naming both licences. `licences.csv` today has `attribution_text` for `lov2`, `odbl`, `cdla` only (verified rows below).
   - Recommendation: add `dual` with reviewed text in the same migration/CSV change; the attribution logic (`_render_attribution`, `export.py:219-234`) already lists it when present.

6. **Category canonical choice.** Recommendation: max `places` per `category_slug` (Pitfall 4). The planner should record the rule, not the outcome.

7. **Is the 8-field set still the right scope after the live check?** D-07 is locked. Pitfall 9 shows the write types differ across the 8; the planner should confirm all 8 are writable (the write schema lists all 8, so yes; see A1).

8. **Where do the secrets live for CI and the functional suite?** The functional suite must not call the real API (testing.md, "Tests never call a real API"). Recommendation: the stub is the only client in tests; the real call is a manual checkpoint.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | ✓ | 3.14.0 in the local venv (`requires-python >=3.12`, `pyproject.toml`) | — |
| `uv` | Dependency promotion, `uv lock`, test runs | ✓ | — (`uv run --offline` worked this session) | — |
| `httpx` | The client and the stub | ✓ | 0.28.1 (locked, `uv.lock:580`) | — |
| PostgreSQL + PostGIS (dev 55433, test DB `letmegetin_test`) | Functional tests, journal, feed | not probed (A10) | — | Integration-only run; functional tests skip via `require_database` (`tests/db.py`). |
| AccesLibre API key | Live probe and first real PATCH | ✗ (none exists) | — | Stub only; the first real call is a blocking human checkpoint (D-13). |
| AccesLibre API (public docs / OpenAPI) | Contract research | ✓ (live `/api/openapi` HTTP 200, fetched 2026-11-15) | — | — |
| Secrets manager (Infisical, `scripts/with-secrets.sh`) | Key injection | exists (`scripts/with-secrets.sh` present); not exercised | — | — |

**Missing dependencies with no fallback:**
- The AccesLibre key. The phase can build and test everything against the stub, but the first real GET/PATCH is blocked on a human.

**Missing dependencies with fallback:**
- Postgres: if down, functional tests skip; they must not be treated as passed (report the skip).

## Validation Architecture

> Nyquist validation is enabled (`.planning/config.json`: `"nyquist_validation": true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.2+ with pytest-asyncio (`asyncio_mode = "auto"`), `--import-mode=importlib` (`pyproject.toml`, `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`); kind tagging by folder in `tests/conftest.py` (`pytest_collection_modifyitems`) |
| Quick run command | `uv run pytest -m unit -q` |
| Full suite command | `uv run pytest -q` (plus `-m integration`, `-m functional`; DB required for functional) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PART-01 | Feed includes only rows where `can_redistribute(source_license, 'lov2_partner')` is true (lov2 and dual, never odbl/cdla) | unit + functional | `uv run pytest tests/functional/places/test_lov2_export.py::test_lov2_feed_excludes_odbl_and_cdla -x` | ❌ Wave 0 |
| PART-01 | Rows keyed on their identifier; no identifier → mapping document, never the feed (D-05) | unit | `uv run pytest tests/unit/domain/places/test_lov2_projection.py -x` | ❌ Wave 0 |
| PART-01 | Category inverse: each `category_slug` resolves to exactly one canonical `activite`; a missing row is unmappable (D-06) | unit | `uv run pytest tests/unit/domain/places/test_lov2_projection.py::test_category_inverse_is_canonical -x` | ❌ Wave 0 |
| PART-01 | Exactly the 8 `FIELD_MAP` criteria are emitted; every other criterion is listed in the mapping document with a reason (D-07, D-08) | unit | `uv run pytest tests/unit/domain/places/test_lov2_projection.py::test_criteria_outside_field_map_are_listed -x` | ❌ Wave 0 |
| PART-01 | Partner archive is written outside `export_dir`; public route returns 404 for it; `latest.json` untouched (Pitfall 1) | functional | `uv run pytest tests/functional/places/test_lov2_export.py::test_partner_archive_not_served -x` | ❌ Wave 0 |
| PART-01 | Mapping document lists every unmappable place with an identifier-or-reason row, and the CSV loader fails on a gap (fail-closed) | functional | `uv run pytest tests/functional/places/test_lov2_export.py::test_mapping_document_names_every_unmappable_place -x` | ❌ Wave 0 |
| PART-02 | Diff returns only fields that differ after typed normalisation (Pitfall 9) | unit | `uv run pytest tests/unit/domain/places/test_acceslibre_push.py::test_diff_is_typed_not_string -x` | ❌ Wave 0 |
| PART-02 | Freshness: user answer (`observed_at` NULL) uses `recorded_at`; their newer `updated_at` skips and journals (Pitfall 5) | unit | `uv run pytest tests/unit/domain/places/test_acceslibre_push.py::test_freshness_uses_recorded_at_for_user_answers -x` | ❌ Wave 0 |
| PART-02 | Payload carries only schema fields; never `user_id` (Pitfall 10) | unit | `uv run pytest tests/unit/domain/places/test_acceslibre_push.py::test_payload_has_no_user_id -x` | ❌ Wave 0 |
| PART-02 | Invalid type is rejected, not coerced to null (Pitfall 7) | unit | `uv run pytest tests/unit/domain/places/test_acceslibre_push.py::test_unknown_value_is_refused -x` | ❌ Wave 0 |
| PART-02 | HTTP adapter: GET then PATCH against a `MockTransport` stub; 429 retried with bounded attempts; 401/403 aborts the run | integration | `uv run pytest -m integration tests/integration/acceslibre/test_client.py -x` | ❌ Wave 0 |
| PART-02 | RPA-locked ERP (403 with its message) is journaled as skipped and the run continues | integration | `uv run pytest tests/integration/acceslibre/test_client.py::test_rpa_403_is_skipped -x` | ❌ Wave 0 |
| PART-02 | `--dry-run` prints the diff and writes nothing (no PATCH, no journal row) | functional | `uv run pytest tests/functional/places/test_acceslibre_push.py::test_dry_run_writes_nothing -x` | ❌ Wave 0 |
| PART-02 | Replayed run after a successful push produces no PATCH and no new accepted event (idempotent, D-12) | functional | `uv run pytest tests/functional/places/test_acceslibre_push.py::test_replay_is_idempotent -x` | ❌ Wave 0 |
| PART-02 | Every decision journaled, losing value kept (D-12) | functional | `uv run pytest tests/functional/places/test_acceslibre_push.py::test_every_decision_journaled -x` | ❌ Wave 0 |
| PART-02 | The API key never appears in logs or exceptions; the host is fixed to the AccesLibre origin | unit | `uv run pytest tests/unit/infrastructure/acceslibre/test_client_security.py -x` | ❌ Wave 0 |
| PART-02 | Import cannot overwrite a user row (existing `_rejection` path, already covered) | functional | `uv run pytest tests/functional/places/test_provenance_conflict.py -x` | ✅ exists |
| — | Licence re-stamp migration: `user` rows move to `dual`, nothing else | functional | `uv run pytest tests/functional/test_licence_migration.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest -m unit -q` (under a few seconds; no DB)
- **Per wave merge:** `uv run pytest -m "unit or integration" -q`
- **Phase gate:** full suite green, plus `uv run ruff check . && uv run ruff format --check .`, `uv run mypy`, `uv run bandit -r src -c pyproject.toml`. Coverage floor 85 % line + branch in CI (AGENTS.md).

### Wave 0 Gaps
- [ ] `tests/integration/acceslibre/__init__.py`, `tests/integration/acceslibre/test_client.py` — `MockTransport`-backed client tests (kind `integration`, auto-tagged by folder)
- [ ] `tests/unit/infrastructure/acceslibre/test_client_security.py` — key redaction and fixed host (kind `unit` only if no socket and no DB are touched; a mocked transport is `integration`, so place accordingly)
- [ ] `tests/unit/domain/places/test_acceslibre_push.py`, `tests/unit/domain/places/test_lov2_projection.py`
- [ ] `tests/functional/places/test_acceslibre_push.py`, `tests/functional/places/test_lov2_export.py` — real PostGIS via `tests/db.py`
- [ ] `tests/functional/test_licence_migration.py` — the `dual` re-stamp
- [ ] Shared fixtures: a stub AccesLibre handler kept in one kit file (`tests/integration/acceslibre/fakes.py`), never copied into each file (testing.md, "Shared fakes … move to a kit file")
- [ ] Settings override helper: monkeypatch `settings.acceslibre_api_key` (new field) in the fixture, never read a real key (testing.md)
- [ ] Framework install: none (pytest, pytest-asyncio, httpx present)

## Security Domain

> Required: `security_enforcement: true` (absent = enabled), `security_asvs_level: 1`, `security_block_on: high`. This phase handles a partner API key and an outbound write to a third party.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (service credential) | `Authorization: Api-Key <key>` (docs, live), key from settings / Infisical, never logged |
| V3 Session Management | no | No user session is created by the push |
| V4 Access Control | yes | Push is an operator CLI only (AGENTS.md: no HTTP endpoint may mutate data); licence gate fail-closed (`can_redistribute`); RPA 403 respected |
| V5 Input Validation | yes | Typed validation of each outbound value before PATCH (Pitfall 7); enum/range checks; reject, never coerce |
| V6 Cryptography | yes | TLS only via httpx default `verify=True`; never disable verification; no hand-rolled signing |
| V7 Error Handling and Logging | yes | Never log the `Authorization` header or the key; exception messages carry the slug and status only |
| V8 Data Protection | yes | Only `value` leaves (Pitfall 10); no `user_id`, no `actor`, no journal rows in the request body; mapping document holds no personal data |
| V9 Communications | yes | Fixed origin `https://acceslibre.beta.gouv.fr` (see threat table); no redirect following to another host (httpx default does not follow redirects; keep it that way, see A-note below) |
| V12 Files and Resources | yes | Partner archive outside the served export directory (Pitfall 1); atomic write (existing `_write_zip`, `os.replace`) |
| V13 API and Web Service | yes | Explicit timeouts; serial requests; bounded retries on 429/5xx; respect `Retry-After` when present (A4) |
| V14 Configuration | yes | Key via `LETMEGETIN_ACCESLIBRE_API_KEY` in Infisical only; no value in the repo; staging key for development (the public docs recommend staging for writes) |

**Note on redirects:** httpx `Client` does not follow redirects by default (`follow_redirects=False`). Keep the default; a redirect to another host would forward the key. [ASSUMED: httpx default; confirm against 0.28.1 in the adapter test.]

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Key sent to a configurable or attacker-set host (SSRF-style exfiltration) | Information disclosure | Base URL is a constant in the adapter. Do not expose it as a setting. Test: the client refuses any other origin. |
| Partner receives a row whose licence does not allow `lov2_partner` (licence leak) | Information disclosure | `can_redistribute` gate in the owned-row query plus a test with an `odbl` row (Pitfall 3) |
| Silent deletion of their data through type coercion | Tampering | Typed validation before PATCH; the API cannot turn `true`/`false` into `null` by its own rule, but a coerced `None` would be applied (Pitfall 7) |
| Overwrite of a fresher AccesLibre correction | Tampering | Read-then-diff plus the freshness rule (D-10, D-11, Pitfall 5) |
| Replay or double push | Repudiation / Tampering | Idempotent diff: a second run sees equality and writes nothing; journal of every decision (D-12) |
| API key in logs, Sentry events or exception text | Information disclosure | Redact at the adapter boundary; test that a forced error does not contain the key |
| Partner archive publicly downloadable from the ODbL route | Information disclosure | Separate directory (Pitfall 1); functional test that the route returns 404 |
| Partner over-load and bans | Denial of service (against them) | Serial requests with a pause; bounded attempts; halt on 429 after the bound (A5: no published quota) |
| Personal data (`user_id`) to a third party | Information disclosure | Only `value` is serialised (Pitfall 10) |

## Sources

### Primary (HIGH confidence — fetched this session)
- `https://acceslibre.beta.gouv.fr/api/openapi` — live OpenAPI 3.0.2 document, HTTP 200, fetched 2026-11-15. Used for: the `Api-Key` header line, business rules, the `ErpImport` write schema (`accessibilite:` at line 2643, the 8 fields at lines 2649–2936), the `Erp` read schema (`accessibilite:` line 1821, `updated_at:` line 2466), the `partialUpdateErp` 200 → `ErpImport` response, and the 429 wording. The saved full output is in the opencode tool-output store.
- `https://acceslibre.beta.gouv.fr/api/docs/` (HTML, fetched 2026-11-15) — Swagger shell; its `requestInterceptor` sets `request.headers['Authorization'] = "Api-Key "`, and the page points at `/api/openapi`.
- `https://acceslibre.beta.gouv.fr/api/erps/` — anonymous GET, HTTP 403 (fetched 2026-11-15). Consistent with the upstream permission class; a live observation about the unkeyed case only.
- `https://acceslibre.beta.gouv.fr/api/schema/` — 404 (not a valid endpoint; not used).
- `https://schema.data.gouv.fr/MTES-MCT/acceslibre-schema/latest/documentation.html` — 404 (the schema documentation link did not resolve; A9).

### Secondary (MEDIUM confidence — upstream source, unpinned)
- `https://raw.githubusercontent.com/MTES-MCT/acceslibre/master/api/urls.py` — routes (`erps`, `accessibilite`, `activites`, `openapi`, `docs/`). [CITED]
- `https://raw.githubusercontent.com/MTES-MCT/acceslibre/master/api/views.py` — `ErpViewSet` (`http_method_names = ["get", "post", "patch"]`, `lookup_field = "slug"`), `ErpPagination` (`page_size = 20`, `max_page_size = 1000`), `API_DOC_SUMMARY`. [CITED — master, not the deployed revision; A6]
- `https://raw.githubusercontent.com/MTES-MCT/acceslibre/master/api/permissions.py` — `IsAllowedForAction`, `CanModifyErp`. [CITED]
- `https://raw.githubusercontent.com/MTES-MCT/acceslibre/master/erp/imports/serializers.py` — `NullBooleanField`, `ErpImportSerializer` (`accessibilite`, the partial-update branch). [CITED]
- `https://raw.githubusercontent.com/MTES-MCT/acceslibre/master/api/serializers.py` — `AccessibiliteSerializer` (`exclude = ("created_at", "updated_at", "completion_rate")`), `ErpSerializer` (`accessibilite` inline, `updated_at`, `source_id`, `sources`). [CITED]
- `https://github.com/MTES-MCT/acceslibre` — repository landing page; confirms the repo, MIT licence, and that the code is public. [CITED]

### In-repo (VERIFIED by reading this session; quotes in the sections above)
- `.planning/phases/15-acceslibre-round-trip/15-CONTEXT.md` (full read)
- `.planning/REQUIREMENTS.md:184-185` — PART-01 and PART-02 text (quoted in §Phase Requirements)
- `src/letmegetin/application/places/export.py` — `DESTINATION` at `:61`; `_write_zip` `:237-323`; `export_odbl` `:341-472`; `_prune_deltas` `:326-338`
- `src/letmegetin/domain/places/export_plan.py` — headers `:35-77`, `FREE_TEXT_COLUMNS` `:82-86`, `build_manifest` `:279-312`, `ExportPlanRepository` `:331`
- `src/letmegetin/domain/places/licence.py` — `DESTINATIONS` `:15`, `can_redistribute` `:18-30`
- `src/letmegetin/infrastructure/persistence/export_repositories.py` — `_licence_allows` `:64-78`, `_answer_may_leave` `:81-83`, `_ranked_answers` `:96-133`, `stream_canonical_places` `:273-330`, `stream_answers` `:332-362`
- `src/letmegetin/infrastructure/persistence/licence_repositories.py:23-36` — `_may_leave` (the SQL twin; CONTEXT's name exists here, not in the export path)
- `src/letmegetin/domain/places/acceslibre_map.py:21-30` — `FIELD_MAP` (quoted above)
- `src/letmegetin/infrastructure/persistence/repositories.py` — `_rejection` `:392-411`; `upsert_accessibility` signature `:1058-1066`, source licence resolution `:1078`, `:1114`, `:1127`; `observed_at` / `recorded_at` writes `:1128-1150`; `_source_licence` `:842-856`
- `src/letmegetin/application/places/contribute.py:33-41` — stored user value and `observed_at=None`
- `src/letmegetin/application/places/import_acceslibre.py:36-48` (`_COLUMNS`), `:265-267` (`make_slug`, `source_id`)
- `src/letmegetin/admin.py` — `import_app` `:115`; `export_app` `:118`; `app.add_typer(export_app, name="export")` `:130`; `@import_app.command("acceslibre")` `:651`; `export_odbl` call `:919-926`; `@export_app.command("odbl")` `:905`
- `src/letmegetin/api/v1/export.py:34`, `:41`, `:54`, `:58-59` — the served directory and the name check
- `src/letmegetin/config.py:13` (`env_prefix="LETMEGETIN_"`), `:20` (`export_dir`), `:21` (`jwt_secret`)
- `src/letmegetin/infrastructure/persistence/models.py:331-336` — `place_accessibility_write` CHECKs; `:419-426` — `SourceLicenceModel` (`source` is the primary key)
- `data/referential/licences.csv` (header and rows, verbatim): line 1 `slug;name;url;obligations;attribution_text`; line 2 `lov2;Licence Ouverte v2.0 (Etalab 2.0);https://www.etalab.gouv.fr/licence-ouverte-open-licence/;attribution;« Source » : nom du producteur et date de dernière mise à jour.`; line 3 `odbl;Open Database License 1.0;https://opendatacommons.org/licenses/odbl/1-0/;attribution|share_alike|keep_open;© contributeurs — base de données sous ODbL 1.0 : toute base dérivée reste sous ODbL (partage à l'identique) et doit rester ouverte tant qu'elle est utilisée.`; line 4 `cdla;Community Data License Agreement - Permissive 2.0;https://cdla.dev/permissive-2-0/;;Contains data provided by the data provider(s) under CDLA-Permissive 2.0.` — **no `dual` row yet**.
- `data/referential/licence_destinations.csv` (all 10 lines, verbatim): `licence_slug;destination;allowed;note` · `lov2;open_export;true;Permissive, attribution only` · `lov2;osm;true;Permissive, attribution only` · `lov2;lov2_partner;true;Our own lov2 data to a lov2 destination` · `odbl;open_export;true;The project's own output licence` · `odbl;osm;true;Same licence as OSM` · `odbl;lov2_partner;false;OSM-derived never to a lov2 destination (LIC-03)` · `cdla;open_export;true;Permissive, no obligation` · `cdla;osm;true;Permissive, no obligation` · `cdla;lov2_partner;false;Not our data, no partner grant`. **No `dual` rows yet.**
- `data/referential/source_licences.csv` (verbatim): `source;licence_slug;effective_from` · `acceslibre;lov2;2026-10-26` · `user;odbl;2026-10-26`
- `data/referential/acceslibre_categories.csv` (header and 3 sample rows, verbatim; 392 lines; 391 data rows, 133 distinct `category_slug`): `activite;category_slug;places` · `Mairie;city_hall;38006` · `Restauration rapide;fast_food_restaurant;37044` · `Coiffure;hair_care;31293`
- `data/referential/families.csv` — contains `entree-acces`, `entree-largeur-de-porte-cm`, `entree-obstacles-a-la-porte-d-entree`, `entree-ouverture-de-porte`, `circulation-circulation-dans-les-allees`, `services-et-equipements-sanitaires`, `exterieur-place-gig-gic-a-proximite`, `exterieur-transports-accessibles-a-proximite` (confirmed by grep: the 8 slugs occur; the criterion seed file itself was not located)
- `pyproject.toml:7-19` (dependencies), `:26-33` (dev group incl. `httpx>=0.27.0` at `:29`), `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`, markers)
- `uv.lock:579-580` — `httpx` `0.28.1`
- `tests/conftest.py`, `tests/db.py` (`require_database`, `seed_source_licences`, `rows`, `scalar`), `tests/functional/conftest.py` (`reviewed_source_licences`, `client`), `tests/functional/places/test_export.py` (CLI runner + export pattern)
- `migrations/versions/` — latest `0013_licence_attribution_text.py` (`0011`, `0012`, `0013` present)
- `docs/rules/testing.md`, `docs/rules/security.md`, `docs/rules/index.md`, `docs/rules/agents.md`, `AGENTS.md`, `PRODUCT.md:35,52`, `docs/partners.md:17` (licences shown on records; no contribution-terms clause found)
- `.planning/config.json` — `nyquist_validation: true`, `security_enforcement: true`, `security_asvs_level: 1`, `commit_docs: true`

**Not read (and why):** `.env` (blocked by the secret-file guard, not needed; `.env.example` is absent). `src/letmegetin/application/referential/licences.py` in full (only the `source_licence` upsert lines `:145-208` were grep-checked).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (httpx version verified in the lock and run in the venv).
- AccesLibre schema shape (write and read): HIGH for the live schema, MEDIUM for upstream internals (unpinned master), LOW for runtime behaviour (no key; A1, A2).
- Architecture and reuse surface: HIGH (every cited path read this session).
- Pitfalls: HIGH for the code-verified ones (1, 4, 6, 7-code, 10); MEDIUM for the ones that depend on the partner (2, 5, 8).
- Validation architecture: MEDIUM (test names are proposals; the Postgres test DB is unprobed, A10).

**Research date:** 2026-11-15
**Valid until:** 14 days for the AccesLibre API claims (a live, partner-controlled schema can change); 30 days for the in-repo reuse surface.

## Project Constraints (from AGENTS.md)

Directives the planner must verify compliance against (these carry the same weight as locked decisions):
- Read `docs/rules/index.md` before the first branch or commit; delivery, testing, language and security rules live there (AGENTS.md).
- **Python:** 3.12+; `from __future__ import annotations` in every module; type hints on all signatures; `str | None`, `list[...]`, `dict[...]`; line length 100; ruff-sorted imports; SQLAlchemy 2.0 typed models (`Mapped[...]`, `mapped_column`); JSONB i18n `{"fr": …, "en": …}`; no comments that restate code; comment the *why*; always `raise … from exc` in `except` blocks.
- **Architecture:** `api → application → domain ← infrastructure`. `domain/` is pure (no SQLAlchemy, no FastAPI, and by extension no httpx).
- **Write path:** the operator CLI (`letmegetin.admin`) is the only write path; **no HTTP endpoint mutates data** until auth exists (Phase 5). The push must be a CLI command (D-14 agrees).
- **Testing:** pytest with pytest-asyncio and `httpx`/`TestClient`; layout `tests/unit`, `tests/integration`, `tests/functional`, each mirroring `src/letmegetin`; tagged for `-m unit|integration|functional`; tests run against their own database (`tests/conftest.py`); the coverage floor is 85 % (line + branch) in CI.
- **Commands:** `uv run pytest`, `uv run ruff check . && uv run ruff format --check .`, `uv run mypy`, `uv run bandit -r src -c pyproject.toml`.
- **Security:** never commit secrets; `.env` is git-ignored; production secrets live in exactly one Infisical project (`INFISICAL_PROJECT_ID=39c0bbf4-d1c8-476e-ae35-8d82c998d704`, `INFISICAL_ENVIRONMENT=prod`, `INFISICAL_PATH=/`); every production command goes through `./scripts/with-secrets.sh <cmd>`; never `--env-file` a `deploy/.env.prod` on a server; never create a second Infisical project or organisation.
- **Graph discipline (AGENTS.md, GitNexus):** run `impact` upstream before editing any function or class; run `detect_changes` before committing; the index was `lastCommit 64d2b27`, HEAD is `0cd76ad` (the index is stale: reindex before trusting graph answers). This research edited no code, so no impact analysis was run.
- **Commit convention:** `.githooks/commit-msg` enforces it; formats are in `docs/rules/delivery.md` (not read in this session).
- **Language:** English everywhere in code and docs except the product copy (`docs/rules/language.md`). This file is English.
- **Agent reporting:** report the checks actually run; name the skipped ones (`docs/rules/agents.md`). Checks skipped in this research are listed in the Metadata and Environment sections.
