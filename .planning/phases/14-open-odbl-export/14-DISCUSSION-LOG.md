# Phase 14: Open ODbL export - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-14
**Phase:** 14-open-odbl-export
**Areas discussed:** Format and transport, Row scope, Attribution and dates, Access and freshness, Change journal, Production publishing

---

## Format and transport

| Option | Description | Selected |
|--------|-------------|----------|
| ZIP of CSV + manifest | places/categories/criteria/answers/aliases CSV + manifest.json | ✓ |
| Single JSONL | one line per place with nested answers | |
| Paginated endpoint | no file, partner iterates the API | |

**User's choice:** ZIP of CSV + manifest.
**Notes:** 635k places / 1.7M answers make a bulk file the only workable shape; a paginated endpoint would turn a dump into 635k requests.

---

## Row scope — place vs answer exclusion

| Option | Description | Selected |
|--------|-------------|----------|
| Per-answer exclusion | place stays, only non-redistributable answers are omitted and counted | ✓ |
| Whole-place exclusion | one blocked answer drops the entire place | |
| Two separate exports | owned-only plus filtered-complete | |

**User's choice:** Per-answer exclusion.
**Notes:** Aligns with D-14 of phase 12 (count what is excluded rather than discard the entity); a place is never lost because of one answer.

---

## Row scope — empty and merged places

| Option | Description | Selected |
|--------|-------------|----------|
| Canonical only + aliases.csv | all canonical places including zero answers; merged places only as alias → canonical | ✓ |
| All places incl. merged | export merged rows with canonical_id | |
| Skip places without answers | reduces volume, breaks "complete referential" | |

**User's choice:** Canonical only + aliases.csv.
**Notes:** The aliases file doubles as the tombstone stream for incremental consumers, since nothing is ever deleted.

---

## Attribution and dates

| Option | Description | Selected |
|--------|-------------|----------|
| ATTRIBUTION.txt + manifest, source-first dates | cumulative text in both files; observed_at then retrieved_at; generated_at | ✓ |
| Generation date only | fails the AccesLibre attribution requirement | |
| Attribution repeated per row | redundant across 1.7M rows | |

**User's choice:** ATTRIBUTION.txt + manifest, source-first dates.

---

## Access and freshness

| Option | Description | Selected |
|--------|-------------|----------|
| CLI → static ZIP | generated file served, no per-request generation | |
| On-demand endpoint | streams a freshly generated ZIP per request | |
| Snapshot + incremental immediately | full snapshot plus deltas from the first release | ✓ |

**User's choice:** Snapshot + incremental immediately.

---

## Incremental contract

| Option | Description | Selected |
|--------|-------------|----------|
| Delta on `updated` + aliases as tombstones | no new table | |
| Additive delta only | no tombstones, partner cannot detect merges | |
| Replayable event journal | append-only history the partner replays | ✓ |

**User's choice:** Replayable event journal.
**Notes:** The user then asked for the most durable design: the journal must also serve a per-place modification history. "Le plus propre et le plus solide."

---

## Journal shape

| Option | Description | Selected |
|--------|-------------|----------|
| Full row snapshot | payload = complete entity state after write; idempotent replay, readable history | ✓ |
| Field diff | compact, but replay must reconstruct state | |
| Id + op, re-read live | cannot serve history, delta depends on the live DB | |

**User's choice:** Full row snapshot.

---

## Journal origin

| Option | Description | Selected |
|--------|-------------|----------|
| Starts at first snapshot | baseline snapshot + events over it; no reconstruction | ✓ |
| Derive from created/updated | no new table, unreliable replay | |
| Journal first, export later | delays delivery for no measurable gain | |

**User's choice:** Table starting at the first snapshot (with the reliability requirement expressed above).

---

## History surface

| Option | Description | Selected |
|--------|-------------|----------|
| `admin place history <slug>` | CLI read, date/op/actor/changed fields | ✓ |
| Public API endpoint | internal history exposed without auth | |
| Journal only, read later | nothing proves the journal is usable | |

**User's choice:** CLI `admin place history`.

---

## Production publishing

| Option | Description | Selected |
|--------|-------------|----------|
| Host systemd timer + manual GitHub dispatch | `scripts/export-odbl.sh` with `docker compose run` and Infisical; no secret in Actions | ✓ |
| Scheduled GitHub workflow over SSH | duplicates the secrets path already on the host | |
| Cron inside the API container | stateless container under traffic | |

**User's choice:** Host systemd timer + `workflow_dispatch`.
**Notes:** The user pushed back on a local-only CLI: "Ma cli local n'aura pas accès à la prod" — the production answer is part of the phase contract.

---

## the agent's Discretion

- CSV column names and ordering; ZIP entry naming beyond the seven agreed files.
- `answers.csv` keyed by slug or numeric id (either satisfies the stable-id requirement).
- Exact ATTRIBUTION wording beyond the legally required elements.
- Whether `latest.json` is written by the CLI or computed by the API on read.

## Deferred Ideas

- Web UI for place history.
- Per-partner export feeds and per-partner keys.
- Parquet / GeoPackage / spatial export and format negotiation.
- Backfilling pre-journal history from `created`/`updated`.
- Destination-specific exports (AccesLibre, OSM, Overture) — phases 15–17.
