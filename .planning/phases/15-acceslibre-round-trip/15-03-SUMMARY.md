---
phase: 15-acceslibre-round-trip
plan: 03
subsystem: api
tags: [acceslibre, probe, alembic, typer, httpx-mocktransport, identifier-rule]

# Dependency graph
requires:
  - phase: 15-acceslibre-round-trip
    provides: the fixed-origin AccesLibre adapter (list_erps / get_erp) and resolve_identifier from 15-02
provides:
  - the nullable `place.erp_slug` column (migration 0014) the feed and push will read
  - `data/referential/acceslibre_identifier_rule.csv` (header `rule;detail`, default `blocked;UNVERIFIED`)
  - `acceslibre probe <source_id>`, the read-only command that settles the identifier and prints A2
affects: [15-04-lov2-feed, 15-05-push-use-case, 15-06-journal]

actuals:
  tokens: 2827
  tasks: 1
  commits: 1
plan_head_before: 82fc629271df98d3084bc60815ed8312f6c17f93
plan_head_after: a2914ee

tech-stack:
  added: []
  patterns:
    - "a probe that writes a reviewed CSV rule: the outcome is data resolve_identifier reads, not a branch"
    - "fail closed on a missing partner key before the client is even constructed"

key-files:
  created:
    - migrations/versions/0014_place_erp_slug.py
    - data/referential/acceslibre_identifier_rule.csv
    - tests/integration/acceslibre/test_probe.py
  modified:
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/admin.py

key-decisions:
  - "The probe writes the rule only after every call succeeded, so a 4xx leaves the previous rule in place — no half-verified identifier reaches the feed."
  - "The rule CSV detail text avoids `;` so the file needs no CSV quoting and stays readable in a diff; 15-04's loader reads it with a plain `;` DictReader."
  - "The command resolves the rule and prints A2 from the same read-only call set; A1 (the PATCH success shape) is deliberately NOT claimed — a read cannot establish it (15-05 gates it)."

patterns-established:
  - "`probe_identifier(client, source_id, path)` is the testable seam: the typer command only builds the keyed client, so the stub suite needs no monkeypatching of typer."

requirements-completed: [PART-01, PART-02]

coverage:
  - id: D1
    description: "Nullable `place.erp_slug` (String 255) via migration 0014, applying from 0013 and dropping cleanly"
    requirement: PART-02
    verification:
      - kind: other
        ref: "LETMEGETIN_DATABASE_URL=…/letmegetin_test uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head; psql: place.erp_slug = character varying(255), nullable"
        status: pass
    human_judgment: false
  - id: D2
    description: "`data/referential/acceslibre_identifier_rule.csv` committed as `blocked;UNVERIFIED`, the safe default that diverts every row to the mapping document"
    requirement: PART-01
    verification:
      - kind: other
        ref: "cat data/referential/acceslibre_identifier_rule.csv -> 'blocked;UNVERIFIED — run ...'"
        status: pass
    human_judgment: false
  - id: D3
    description: "`acceslibre probe <source_id>`: two read-only lookups, one get_erp printing the accessibilite section keys (A2), then the resolved rule written to the CSV; missing key exits 1 without a call"
    requirement: PART-02
    verification:
      - kind: integration
        ref: "tests/integration/acceslibre/test_probe.py"
        status: pass
      - kind: other
        ref: "env -u LETMEGETIN_ACCESLIBRE_API_KEY uv run python -m letmegetin.admin acceslibre probe 12345 -> exit 1, no network call"
        status: pass
    human_judgment: false
  - id: D4
    description: "The first real (read-only) probe against AccesLibre records the identifier rule and the A2 accessibilite keys"
    verification: []
    human_judgment: true
    rationale: "Requires the AccesLibre partner API key that does not exist yet (D-13, 15-PARTNER-ASK.md); it is plan Task 2, a checkpoint:human-action gate=blocking-human that was NOT run and NOT simulated."

duration: 5min
completed: 2026-11-15
status: halted
---

# Phase 15 Plan 03: AccesLibre identifier probe Summary

**A read-only `acceslibre probe` that settles the ERP identifier and prints the A2 read contract, plus the `erp_slug` column and a `blocked;UNVERIFIED` rule that keeps the feed fail-closed until a real key exists**

## Performance

- **Duration:** 5 min
- **Started:** 2026-11-15T18:17:00Z
- **Completed:** 2026-11-15T18:21:56Z
- **Tasks:** 1 of 2 (Task 2 is the blocking-human probe, not executed)
- **Files modified:** 5

## Accomplishments

- `PlaceModel.erp_slug` (nullable `String(255)`) with migration `0014`: applies from `0013`, downgrades to it, re-applies, verified column-by-column on `letmegetin_test`.
- `data/referential/acceslibre_identifier_rule.csv` committed with the plan's safe default `blocked;UNVERIFIED`: until a live probe overwrites it, `resolve_identifier` returns `None` for every row, so the feed and the push divert rows to the mapping document instead of keying on an unverified `origin_id`.
- `acceslibre probe <source_id>` calls `list_erps(uuid=…)` and `list_erps(source="acceslibre", source_id=…)`, prints each ERP's `slug`/`source`/`source_id`, calls `get_erp(<slug>)` and prints the `accessibilite` section keys (A2), then records `origin_id` / `slug` / `blocked` plus a detail line. It never claims A1.
- The command fails closed: no `LETMEGETIN_ACCESLIBRE_API_KEY` prints one error and exits 1 before any client is constructed — there is no unauthenticated fallback.
- Five stub-backed integration tests prove the three rule outcomes, both lookups, the A2 print, and that a refusal writes no rule.

## Task Commits

Each task was committed atomically:

1. **Task 1: The erp_slug column, the identifier-rule CSV, and the probe command** - `a2914ee` (feat)
2. **Task 2: Run the first real (read-only) probe** - NOT EXECUTED (`checkpoint:human-action gate="blocking-human"`)

**Plan metadata:** recorded by the close-out commit (docs).

## Files Created/Modified

- `migrations/versions/0014_place_erp_slug.py` — revision `0014` from `0013`: adds/drops `place.erp_slug`.
- `data/referential/acceslibre_identifier_rule.csv` — `rule;detail`, default `blocked;UNVERIFIED`; the probe overwrites the single row.
- `src/letmegetin/infrastructure/persistence/models.py` — `PlaceModel.erp_slug: Mapped[str | None]`.
- `src/letmegetin/admin.py` — `acceslibre_app`, `acceslibre probe`, `probe_identifier`, `_write_identifier_rule`.
- `tests/integration/acceslibre/test_probe.py` — 5 tests over an `httpx.MockTransport` stub; no socket, no key, no database.

## Decisions Made

- **The rule is written last, after every call succeeded.** A 403/429 or a network failure leaves the committed `blocked;UNVERIFIED` row (or a previously verified rule) untouched; a partially observed ERP never becomes an identifier.
- **Detail text carries no `;`.** The rule file therefore needs no CSV quoting and diffs cleanly; 15-04 reads it with a plain `;` `DictReader`.
- **`probe_identifier` is a module-level seam** taking the client, so the stub suite drives the real logic without monkeypatching typer or the settings object.
- **`_run_admin(callback, bump=False, commit=False)` as the plan specifies** — it buys the standard `DomainError` → exit 1 mapping; the session is unused and rolled back.

## Deviations from Plan

None - Task 1 executed exactly as written.

## Issues Encountered

- **The plan is halted at its designed blocking gate (Task 2).** The AccesLibre partner API key does not exist yet (D-13), so the live probe was NOT run, NOT stubbed, and `acceslibre_identifier_rule.csv` was left at the plan's committed `blocked;UNVERIFIED` default. Open Question 1 and A2 therefore remain open; A1 was never in scope here. `requirements-completed` lists the plan's requirement IDs per the summary contract, but `REQUIREMENTS.md` was deliberately not marked: PART-01/PART-02 are only truly satisfied once the live probe records the rule.
- **GitNexus index is stale** (`lastCommit` 47 commits behind HEAD). `impact PlaceModel --direction upstream` returned `risk: MEDIUM`, 12 impacted symbols — the added column is nullable and unread by any caller, so no call site can break; mypy and the integration suite confirm. No reindex was run.

## User Setup Required

The plan's `user_setup` entry is live: `LETMEGETIN_ACCESLIBRE_API_KEY` must be obtained (see `15-PARTNER-ASK.md`) and stored in the Infisical project `39c0bbf4-…`, `prod`, path `/`, injected via `scripts/with-secrets.sh`. No key was read, printed or committed by this plan.

## Next Phase Readiness

- **Ready:** the migration, the rule file and the command are in place; 15-04 can read `data/referential/acceslibre_identifier_rule.csv` and `place.erp_slug` today.
- **Blocked:** 15-04's partner identifier column and 15-05's PATCH target depend on the rule this probe records. Until then the committed default is `blocked`, so every row diverts to the mapping document — fail-closed, by design.
- **To resume:** provide the key, then run `acceslibre probe <origin_id>` (with `scripts/with-secrets.sh`), review the rewritten CSV row and the printed A2 keys, and re-summarize this plan as `complete`.

---

## Self-Check: PASSED

- `migrations/versions/0014_place_erp_slug.py` — FOUND; `upgrade`/`downgrade -1`/`upgrade` all ran on `letmegetin_test`.
- `data/referential/acceslibre_identifier_rule.csv` — FOUND, holds `blocked;UNVERIFIED`.
- `tests/integration/acceslibre/test_probe.py` — FOUND, 5 passed.
- Commit `a2914ee` — ancestor of HEAD.
- Task 2 — intentionally NOT executed (blocking-human checkpoint).

*Phase: 15-acceslibre-round-trip*
*Completed (partial): 2026-11-15*
