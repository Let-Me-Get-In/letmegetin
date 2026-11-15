---
phase: 14-open-odbl-export
verified: 2026-11-14T23:05:48Z
status: passed
score: 25/25 must-haves verified
covered_files:
  - .github/workflows/export-odbl.yml
  - .planning/phases/14-open-odbl-export/14-01-PLAN.md
  - .planning/phases/14-open-odbl-export/14-01-SUMMARY.md
  - .planning/phases/14-open-odbl-export/14-02-PLAN.md
  - .planning/phases/14-open-odbl-export/14-02-SUMMARY.md
  - .planning/phases/14-open-odbl-export/14-03-PLAN.md
  - .planning/phases/14-open-odbl-export/14-03-SUMMARY.md
  - .planning/phases/14-open-odbl-export/14-04-PLAN.md
  - .planning/phases/14-open-odbl-export/14-04-SUMMARY.md
  - .planning/phases/14-open-odbl-export/14-05-PLAN.md
  - .planning/phases/14-open-odbl-export/14-05-SUMMARY.md
  - data/referential/licences.csv
  - deploy/systemd/letmegetin-export-odbl-delta.service
  - deploy/systemd/letmegetin-export-odbl-delta.timer
  - deploy/systemd/letmegetin-export-odbl-snapshot.service
  - deploy/systemd/letmegetin-export-odbl-snapshot.timer
  - docker-compose.prod.yml
  - docs/deploy.md
  - docs/openapi.json
  - docs/public-api.md
  - migrations/versions/0012_export_event.py
  - migrations/versions/0013_licence_attribution_text.py
  - scripts/export-odbl.sh
  - src/letmegetin/admin.py
  - src/letmegetin/api/v1/export.py
  - src/letmegetin/api/v1/router.py
  - src/letmegetin/application/places/attribution.py
  - src/letmegetin/application/places/export.py
  - src/letmegetin/application/places/history.py
  - src/letmegetin/application/referential/licences.py
  - src/letmegetin/config.py
  - src/letmegetin/domain/places/export.py
  - src/letmegetin/domain/places/export_plan.py
  - src/letmegetin/domain/referential/entities.py
  - src/letmegetin/infrastructure/persistence/export_repositories.py
  - src/letmegetin/infrastructure/persistence/licence_repositories.py
  - src/letmegetin/infrastructure/persistence/models.py
  - src/letmegetin/infrastructure/persistence/repositories.py
  - src/letmegetin/main.py
  - tests/functional/api/test_export.py
  - tests/functional/places/test_export.py
  - tests/functional/places/test_export_event.py
  - tests/integration/api/test_openapi.py
  - tests/unit/application/places/test_export.py
  - tests/unit/application/places/test_history.py
  - tests/unit/infrastructure/persistence/test_export_event_chokepoints.py
  - tests/unit/scripts/test_export_odbl_wrapper.py
covered_digest: "v4:sha256:4141c7eaaa6443c42015f4ef39e6f0c7d310a8e5f73531a667ca54f4b2719318"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Load the four systemd units on the Linux host: `systemd-analyze verify deploy/systemd/letmegetin-export-odbl-*.{service,timer}`, then `systemctl enable --now letmegetin-export-odbl-snapshot.timer letmegetin-export-odbl-delta.timer` and read `systemctl list-timers`."
    expected: "No verify errors; the snapshot timer is next due Monday 04:00 and the delta timer daily 03:15; both services run through `/opt/letmegetin/scripts/with-secrets.sh` and exit 0 on a dry run."
    why_human: "This workstation is macOS and has no systemd; the units were only compared structurally with `letmegetin-retention.service`. 14-05 itself records `human_judgment: true` for this item."
  - test: "Run `.github/workflows/export-odbl.yml` (workflow_dispatch) against the real host after setting the `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_SSH_KEY` secrets and the `DEPLOY_HOST_FINGERPRINT` variable, and allowlisting the Actions runner IP for the run."
    expected: "The SSH step connects, the remote `case` accepts the chosen mode, `scripts/export-odbl.sh` runs `docker compose run --rm -T -v export_data:/data/export-rw … --out /data/export-rw`, and a new ZIP plus `latest.json` appear in the served volume."
    why_human: "No host, SSH key or firewall is available in the repo; the workflow is verified for YAML shape, trigger, secrets and `envs` format only (the pinned appleboy/ssh-action action.yml documents `envs: key=value`)."
  - test: "Generate a snapshot against a production-scale copy (≈635k places / 1.7M answers) and record wall time, peak RSS and ZIP size; repeat for a delta."
    expected: "The snapshot completes within the workflow's 2 h timeout and the timers' tolerance with bounded memory (server-side cursor, `yield_per=1000`, no full list); the delta is proportionally small."
    why_human: "The functional suite runs on the tiny test database; no production-scale timing or memory measurement exists in the phase."
  - test: "Read the three `attribution_text` values in `data/referential/licences.csv` (lov2, odbl, cdla) against each licence's actual required wording, and confirm the rendered `ATTRIBUTION.txt` line (`source — legal licence name — last-update date — sentence`) is the attribution the licence expects."
    expected: "Each sentence is confirmed or amended; a change is a reviewed CSV edit followed by `admin licences sync` (the export reads the CSV directly)."
    why_human: "Whether a sentence is the legal wording a licence requires is a legal judgement no test asserts; 14-02 records it as `human_judgment: true`."
  - test: "Read `## ODbL export` in `docs/public-api.md` against the shipped behaviour and confirm it neither over- nor under-claims (delta is one MVCC window, `--since` is the catch-up, attribution lists only present sources, counters are global/current-population not per-archive)."
    expected: "The prose is accepted as the partner contract, or corrected in place; 14-04 records the prose review as `human_judgment: true`."
    why_human: "The tests pin the shared constants and the OpenAPI paths, not the meaning of the delta and counter paragraphs."
---

# Phase 14: Open ODbL export Verification Report

**Phase Goal:** A partner can download the whole referential as ODbL, with attribution rendered in the export.
**Verified:** 2026-11-14T23:05:48Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `export_event` exists with a monotone `BigInteger IDENTITY` `seq`, `xid xid8 NOT NULL DEFAULT pg_current_xact_id()`, and CHECK constraints on `entity`/`op` (14-01) | ✓ VERIFIED | `migrations/versions/0012_export_event.py`; `models.py:362-384`; test DB at `0013 (head)` |
| 2 | `safe_seq()` returns `max(seq) WHERE xid < pg_snapshot_xmin(pg_current_snapshot())`; an in-flight event is excluded and becomes visible after commit (14-01) | ✓ VERIFIED | `export_repositories.py:220-231`; `test_safe_seq_publishes_an_event_only_after_its_transaction_commits` (passed) |
| 3 | Every place-write choke point appends a same-transaction full-row event (add/update/merge/reject-update/reassign/dedup/answers); a rejected or no-op answer appends nothing (14-01) | ✓ VERIFIED | `repositories.py:623-640,692-771,807-827,860-920,1058-1175`; 13 journal functional cases passed. **Residual:** `update()` appends unconditionally, so a future no-op `update()` would append (no production caller today; see Observations) |
| 4 | A rejected answer stays only in `place_accessibility_write`; an accepted new/overwritten answer appends insert/update; re-submitting the identical answer appends nothing (14-01) | ✓ VERIFIED | `test_an_accepted_new_answer…`, `test_overwriting_an_answer…`, `test_resubmitting_the_same_answer…`, `test_a_rejected_answer_stays_in_the_write_journal_only` (all passed) |
| 5 | The event and its write land in the same transaction; rollback removes both, commit persists both; the repository flushes, never commits (14-01) | ✓ VERIFIED | `test_a_rolled_back_write_leaves_no_event_and_no_place` passed; append helper flushes only (`repositories.py:623-640`) |
| 6 | `letmegetin-admin place history <slug>` prints date, op, actor and the read-time changed-field summary in seq order (14-01) | ✓ VERIFIED | `application/places/history.py`; `test_place_history_prints_both_events_in_seq_order` passed |
| 7 | `export odbl` writes exactly `places.csv`, `categories.csv`, `criteria.csv`, `answers.csv`, `aliases.csv`, `ATTRIBUTION.txt`, `manifest.json` (14-02) | ✓ VERIFIED | Independent ZIP run: `ENTRIES` exactly the seven; `test_snapshot_zip_carries_the_seven_files…` passed |
| 8 | Every CSV is UTF-8, comma-separated, RFC 4180 quoted, header row, no BOM; the manifest carries `schema_version`, `generated_at`, `referential_version`, per-file counts, the three exclusion counters and `attribution_ref` (14-02) | ✓ VERIFIED | Independent run parsed every file with `csv.DictReader`, asserted no BOM and round-tripped `Lieu "Bar", côté\njardin`; `test_build_manifest_carries_every_key…` |
| 9 | `places.csv` holds only canonical places, including zero-answer places; merged places appear only in `aliases.csv` as `alias_id → canonical_id` (14-02) | ✓ VERIFIED | Independent run: canonical + zero-answer place present, merged place absent, alias row present; snapshot functional test passed |
| 10 | A merged place's answer is remapped onto the canonical id, ranked by canonical-wins then `recorded_at DESC`, `place_id DESC`, `criterion_id DESC`, and every loser counted per source+licence (14-02) | ✓ VERIFIED | `_ranked_answers` (`export_repositories.py:96-133`); independent run keys the merged answer under the canonical id; `test_answer_precedence…` and snapshot test passed |
| 11 | An answer reaches `answers.csv` only when its own licence **and** its effective canonical place allow `open_export`; withheld answers are absent and counted; the three populations reconcile (14-02) | ✓ VERIFIED | `_answer_may_leave` / `_licence_allows`; independent run omitted the closed-source answer and counted it; `test_the_exported_plus_excluded_plus_withheld_answers_reconcile` passed |
| 12 | `answers.csv` is keyed by `(place_id, criterion_slug)`; place/answer rows carry `source`, `source_license`, `source_url` (nullable) and the source-first date (14-02) | ✓ VERIFIED | Headers and values printed in the independent run; `test_answers_are_keyed_by_place_and_criterion_slug…` passed |
| 13 | `ATTRIBUTION.txt` lists only sources actually present, with legal names/sentences from `data/referential/licences.csv`, the Produced Works sentence and the forward-looking sentence, repeated verbatim in `manifest.attribution`; no per-row column, no hard-coded OSM/Overture line (14-02) | ✓ VERIFIED | Independent run produced only the AccesLibre/lov2 line + both constants; `manifest.attribution == attribution`; `test_render_source_line…`, `test_public_api_documents_the_shared_attribution_sentences` passed |
| 14 | `latest.json` carries `snapshot {name, seq}`, `watermark`, `retention_floor_seq` and `deltas[] {name, from_seq, to_seq}`; a delta publishes only `watermark < seq <= safe_seq()`; the watermark moves only after the ZIP is written/fsynced; `--since` below the floor is refused naming the floor and snapshot (14-02) | ✓ VERIFIED | Independent run printed the exact shape and a refused `--since 61 < floor 62` message; `test_a_delta_publishes_only_the_window…`, `test_a_failed_delta_leaves_the_watermark_untouched`, `test_a_catch_up…`, `test_a_delta_never_skips…` passed |
| 15 | Retention prunes `export_event` to the previous snapshot boundary, removes delta ZIPs the new snapshot subsumes and unlisted orphans, keeps the snapshot ZIPs, and a failed snapshot prunes nothing (14-02) | ✓ VERIFIED | Independent run: floor = first snapshot seq, events ≤ it gone, delta removed, both snapshot ZIPs kept; `test_retention_prunes_to_the_previous_snapshot…`, `test_a_failed_snapshot_prunes_nothing` passed |
| 16 | `GET /api/v1/export/latest.json` serves the CLI-written index, 404 when absent/unreadable, under the anonymous rate limit (14-03) | ✓ VERIFIED | `api/v1/export.py:21-37`; `test_latest_json_serves…`, `…is_404_before…`, `…is_404_when_unreadable` passed |
| 17 | `GET /api/v1/export/{name}.zip` serves an archive and rejects separators, `..`, dotfiles, `.lock`, `.tmp` and out-of-directory symlinks; missing files are 404 (14-03) | ✓ VERIFIED | `api/v1/export.py:52-77`; 9 traversal cases, symlink case and `_is_servable` helper cases passed |
| 18 | The export directory is a named `export_data` volume mounted read-only at `LETMEGETIN_EXPORT_DIR` in `api`, shared with host generation (14-03) | ✓ VERIFIED | `docker-compose.prod.yml`; `docker compose config` renders `source: export_data`, `target: /data/export`, `read_only: true`; env `LETMEGETIN_EXPORT_DIR: /data/export` |
| 19 | `docs/public-api.md` documents both endpoints, the seven entries/columns, per-file origin ids, the MVCC delta contract, the CSV guard allow-list, the per-licence `attribution_text` and the Produced Works statement (14-04) | ✓ VERIFIED | `docs/public-api.md:154-319`; text read in full; `test_openapi_exposes_the_public_contract` passed |
| 20 | The Produced Works and forward-looking sentences in the docs are the shared `application/places/attribution.py` constants, byte-identical to `ATTRIBUTION.txt` (14-04) | ✓ VERIFIED | Independent run asserted both constants in the ZIP; `test_public_api_documents_the_shared_attribution_sentences` passed |
| 21 | `docs/openapi.json` is regenerated (never hand-edited) and carries both export paths (14-04) | ✓ VERIFIED | Ran `scripts/export_openapi.py` twice: identical sha256 `f49d7a1b…`, empty git diff; both paths and `application/zip` present |
| 22 | `scripts/export-odbl.sh {snapshot|delta}` builds the exact argv with one `$OUT`, `run --rm -T`, a read-write volume at a second mount target, `--delta` only in delta mode, no `jq`/`--since`, and exit 2 on an unknown mode (14-05) | ✓ VERIFIED | `scripts/export-odbl.sh`; wrapper unit tests 3 passed; mutation of the expected mount made them fail (not vacuous). Shipped target is `/data/export-rw`, not the plan's literal `/data/export` (same volume, see Observations) |
| 23 | A weekly snapshot (Mon 04:00) and a daily delta (03:15) are four distinct systemd units driven by `with-secrets.sh` (14-05) | ✓ VERIFIED | Four unit files; `ExecStart`/`OnCalendar` asserted. Loading on Linux is a human item |
| 24 | A `workflow_dispatch` workflow SSHes to the host, runs the same wrapper with the chosen mode, and carries no DB/API secret (14-05) | ✓ VERIFIED | `.github/workflows/export-odbl.yml` parses; trigger, `mode` choice, three `DEPLOY_*` secrets, pinned action SHA, `envs: MODE=…` (the action documents `key=value`). Real-host run is a human item |
| 25 | `docs/deploy.md` shows the exact unit lines, the writable generation command, the MVCC delta vs `--since`, the Actions prerequisite/runner-IP allowlist, automatic retention and the atomic AccesLibre import (14-05) | ✓ VERIFIED | `docs/deploy.md` read in full; all required strings present |

**Score:** 25/25 truths verified (0 present-but-behavior-unverified)

### ROADMAP Success Criteria

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | A partner downloads an ODbL export of places, categories, criteria and answers, each row carrying a stable id and its origin id | PRESENT | Seven-entry ZIP verified from the real test DB; `place_id`+`origin_id`/`source`, `(place_id, criterion_slug)`, category/criterion `slug`; every CSV parsed with `csv.DictReader` |
| 2 | The export renders attribution listing only the sources present, with legal names read from `licences.csv` (AccesLibre with source name and last-update date) | PRESENT | Independent `ATTRIBUTION.txt`: `acceslibre — Licence Ouverte v2.0 (Etalab 2.0) — 2026-11-01 — « Source » : …`; no OSM/Overture; the withheld source is absent. Human legal review of the sentence remains |
| 3 | The API and map are documented as Produced Works alongside the export | PRESENT | `PRODUCED_WORKS_SENTENCE` in `attribution.py`, `ATTRIBUTION.txt`, `manifest.attribution` and `docs/public-api.md`; pinned by an integration test |

### Deferred Items

None. No identified item is deferred to a later phase by the roadmap.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `migrations/versions/0012_export_event.py` | journal table with identity seq, `xid8`, checks | ✓ VERIFIED | Applied; test DB at 0013 |
| `migrations/versions/0013_licence_attribution_text.py` | additive nullable column | ✓ VERIFIED | Applied; no backfill, CSV is source of truth |
| `src/letmegetin/domain/places/export.py` | event port, `describe_changes`, fail-closed `_jsonable` | ✓ VERIFIED | `_jsonable` non-finite unit case passed |
| `src/letmegetin/domain/places/export_plan.py` | pure row dataclasses, CSV serialisers, guard, manifest | ✓ VERIFIED | RFC 4180/guard/manifest unit cases passed |
| `src/letmegetin/application/places/export.py` | snapshot/delta/catch-up use case, flock, atomic latest.json, retention | ✓ VERIFIED | Functional + independent run |
| `src/letmegetin/application/places/attribution.py` | present-sources renderer + shared constants | ✓ VERIFIED | Used by export and docs test |
| `src/letmegetin/infrastructure/persistence/export_repositories.py` | `safe_seq`, `seq_at_or_before`, `delete_up_to`, streamed reads, counters | ✓ VERIFIED | No commit in repository; caller commits |
| `src/letmegetin/infrastructure/persistence/repositories.py` | same-transaction journal appends at every choke point | ✓ VERIFIED | 13 functional cases + AST scan |
| `src/letmegetin/api/v1/export.py` | two read-only routes, rate limit, traversal guard | ✓ VERIFIED | 27 functional cases passed |
| `src/letmegetin/admin.py` | `export odbl --out [--delta] [--since]`, `place history` | ✓ VERIFIED | CLI invoked in functional tests; `bump=False` |
| `scripts/export-odbl.sh` | snapshot/delta wrapper, writable second mount | ✓ VERIFIED | `bash -n`; argv test + mutation check |
| `deploy/systemd/letmegetin-export-odbl-{snapshot,delta}.{service,timer}` | weekly/daily units | ✓ VERIFIED (structural) | Load on Linux is human item |
| `.github/workflows/export-odbl.yml` | `workflow_dispatch` SSH, no DB/API secret | ✓ VERIFIED (structural) | Real host is human item |
| `data/referential/licences.csv` | reviewed `attribution_text` | ✓ VERIFIED for presence/use | Legal wording is human item |
| `docs/public-api.md`, `docs/openapi.json`, `docs/deploy.md` | partner + ops contract | ✓ VERIFIED | Read; OpenAPI byte-stable |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `can_redistribute` (domain) | `_licence_allows` / `_answer_may_leave` (SQL) | `licence_destination` EXISTS | WIRED | Same matrix; Phase-12 agreement test plus export withhold tests |
| `ExportPlan` row dataclasses | `csv.writer` | `serialise_rows` / `_write_csv_entry` | WIRED | Unit RFC-4180 + functional ZIP |
| `COALESCE(place.canonical_id, place.id)` | `answers.csv` `place_id` | `ranked_answers` CTE | WIRED | Merged answer emitted under canonical id |
| `safe_seq()` | boundary and streamed rows | REPEATABLE READ transaction, `safe_seq()` first | WIRED | No-gap and delta-window tests |
| `delete_up_to(previous_snapshot.seq)` | journal prune | `export_odbl` retention step | WIRED | Retention test; failed-snapshot test |
| `scripts/export-odbl.sh <mode>` | `letmegetin-admin export odbl --out … [--delta]` | `compose run` argv | WIRED | Wrapper test asserts exact argv |
| `export_data` volume | wrapper `/data/export-rw` ↔ API `/data/export` | Compose named volume | WIRED | `docker compose config` read-only target; wrapper writable second target |
| `application/places/attribution.py` constants | `docs/public-api.md` | integration assertion | WIRED | Test passes |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `places.csv` | place fields, `source_license`, date | `PlaceModel` (DB) via streamed read | Yes — seeded rows and real licence matrix | ✓ FLOWING |
| `answers.csv` | winner per `(canonical_id, criterion_id)` | `_ranked_answers` CTE over `place_accessibility` | Yes — merged answer remapped in the independent run | ✓ FLOWING |
| `aliases.csv` | `alias_id`, `canonical_id` | `place.canonical_id IS NOT NULL` | Yes | ✓ FLOWING |
| `ATTRIBUTION.txt` | source/licence/date/sentence | exported rows' `(source, source_license)` + `licences.csv` | Yes — only AccesLibre present; withheld source absent | ✓ FLOWING |
| `latest.json` | snapshot/watermark/floor/deltas | `safe_seq()` + previous file state | Yes — independent run printed real seqs | ✓ FLOWING |
| `/api/v1/export/*` | served index/archive | `settings.export_dir` files written by CLI | Yes — functional routes serve the written files | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Snapshot ZIP, remap, attribution, delta, floor, retention | `uv run python /tmp/verify_exp14.py` (independent script against the test DB) | `ALL CHECKS PASSED`; seven entries, zero-answer place, merged alias, remapped answers, withheld counter, `--since 61 < floor 62` refusal, subsumed delta removed, both snapshots kept | ✓ PASS |
| Export functional suite | `uv run pytest tests/functional/places/test_export.py -m functional -v` | 9 passed | ✓ PASS |
| Journal functional suite | `uv run pytest tests/functional/places/test_export_event.py -m functional -v` | 14 passed | ✓ PASS |
| Serving/traversal functional suite | `uv run pytest tests/functional/api/test_export.py -m functional -v` | 27 passed (9 traversal URLs + symlink + helper + rate limit) | ✓ PASS |
| Wrapper argv non-vacuity | Mutated the expected `export_data:/data/export-rw` to `/data/export`, ran the wrapper test | 2 failed at index 9 (`…-rw` vs `…`), restored; test is coupled to the real script | ✓ PASS |
| Compose read-only mount | `POSTGRES_PASSWORD=x … docker compose -f docker-compose.prod.yml config` | `source: export_data`, `target: /data/export`, `read_only: true` | ✓ PASS |
| OpenAPI determinism | `uv run python scripts/export_openapi.py` twice, `sha256sum`/`diff` | identical `f49d7a1b…`; empty diff | ✓ PASS |

### Probe Execution

None — the phase declares no `probe-*.sh`; the export is exercised through the functional suite and the independent script above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EXP-01 | 14-01, 14-02, 14-03, 14-05 | Download an ODbL export of places, categories, criteria and answers with stable ids and origin ids | ✓ SATISFIED | Seven-entry ZIP from the real DB; all four row families; stable ids + origin ids; delta/catch-up; read-only serving; host wrapper |
| EXP-02 | 14-02, 14-04 | Attribution listing present sources; API and map documented as Produced Works | ✓ SATISFIED | Present-sources `ATTRIBUTION.txt` + `manifest.attribution`; shared Produced Works/forward-looking constants in docs and ZIP. Legal wording review is a human item |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK` markers in changed files | — | None |
| — | — | No stub returns, no per-request generation, no hard-coded OSM/Overture line, no per-row attribution column | — | None |

### Summary-vs-Code Observations (not blockers)

1. **14-05-SUMMARY says the plan's Task-1 text and argv assertions were updated to `/data/export-rw`; the persisted `14-05-PLAN.md` still says `-v export_data:/data/export` / `--out $OUT` (must_haves and Task 1).** The code, test and runbook use `/data/export-rw`; the plan artifact is stale, not the implementation.
2. **14-05's Task-3 doc assertion checks the substring `run --rm -T -v export_data:/data/export`, which also matches `/data/export-rw`.** The doc itself is correct, but that assertion would pass for the old path too.
3. **14-03's route-level traversal test accepts `400/404/422`; the contract is 404.** The helper-level `_is_servable` test and the symlink containment case pin the guard, and the marker-leak assertion is real, so the guard is not merely route-404 luck.
4. **`SqlAlchemyPlaceRepository.update()` appends unconditionally.** The no-op guarantee is proven for `set_review_state` and `upsert_accessibility`; no production caller calls place `update()` today. If a future caller re-saves an unchanged place, the journal/delta would grow (replay stays idempotent).
5. **Delta `manifest.excluded_places` / `excluded_answers` are computed over the current full population, not the delta window**, while `files` and the CSV rows are window-scoped. The docs do not state this; a partner summing counters across archives could double-count. The counter contract deserves the human docs review below.
6. **The attribution source label is the source slug (`acceslibre`), not a human display name.** The legal licence name (`Licence Ouverte v2.0 (Etalab 2.0)`) and date are present; a cased display name would need a new reviewed data field.

### Human Verification Accepted

Accepted by the operator on 2026-11-15 with the four remaining checks delegated to tickets:
**LET-125** (load the systemd units on a Linux host, run the workflow against the real host) and
**LET-126** (legal review of the three `attribution_text` sentences and of the public export contract).
Nothing here is a code gap; each item needs an environment or a legal judgement this workstation cannot supply.

### Human Verification Required

1. **Load the systemd units on the Linux host**

   **Test:** `systemd-analyze verify deploy/systemd/letmegetin-export-odbl-*.{service,timer}`, then `systemctl enable --now letmegetin-export-odbl-snapshot.timer letmegetin-export-odbl-delta.timer` and `systemctl list-timers`.
   **Expected:** No verify errors; snapshot due Mon 04:00, delta daily 03:15; a manual run through `with-secrets.sh` exits 0.
   **Why human:** macOS has no systemd; the units were only compared structurally with `letmegetin-retention.service`.

2. **Run the `workflow_dispatch` workflow against the real host**

   **Test:** Set `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` secrets and `DEPLOY_HOST_FINGERPRINT` variable, allowlist the runner IP, dispatch `delta` then `snapshot`.
   **Expected:** SSH connects, the remote `case` accepts the mode, the wrapper runs in the one-off container on `export_data:/data/export-rw`, and the served `latest.json`/ZIP update.
   **Why human:** No host, SSH key or firewall is in the repo; only the YAML shape, trigger, secrets and `envs` format were verified.

3. ~~**Measure production-scale timing and memory**~~ — **done on the dev DB (2026-11-15)**, which holds the full
   dataset: `634,931` places and `1,711,095` answers. `letmegetin-admin export odbl` wrote a snapshot of
   `629,473` places / `1,702,243` answers in **45.6 s wall**, **94 MB peak RSS**, **52 MB ZIP**
   (`442 MB` uncompressed), no swap. A delta with an empty journal is near-instant.
   **Found while measuring:** the run first produced a **valid-looking empty export** (`places.csv=0`,
   every row withheld) because the `licence` / `licence_destination` tables were empty on that database —
   the SQL twin fails closed, which is correct, but the CLI said nothing. Fixed in `bc4c22e`: `export odbl`
   now refuses to write when the reviewed matrix is empty, naming `admin licences sync`, with a unit test.
   The operator step after any fresh database stays: `admin licences sync` (or the seed) before exporting.

4. **Review the attribution wording legally**

   **Test:** Read the three `attribution_text` values in `data/referential/licences.csv` against each licence's required wording and confirm the rendered line.
   **Expected:** Sentences confirmed or amended; an amendment is a reviewed CSV edit + `admin licences sync`.
   **Why human:** Legal judgement; 14-02 marks it `human_judgment: true`.

5. **Review the public export contract prose**

   **Test:** Read `## ODbL export` in `docs/public-api.md` against shipped behaviour, including whether the delta manifest's exclusion counters are global or window-scoped.
   **Expected:** Prose accepted or corrected in place.
   **Why human:** Tests pin constants and paths, not the meaning of the delta/counter paragraphs; 14-04 marks it `human_judgment: true`.

### Gaps Summary

No failed must-have. Every ROADMAP success criterion is present and observable in the code: the ZIP is built from real DB rows, the seven entries parse, the remap/licence/attribution rules hold, the MVCC boundary and retention behave, the serving routes are read-only and traversal-safe, and the ops wrapper/timers/workflow exist. Status is `passed`: the four human items above are tracked in LET-125/LET-126 because the systemd units, the Actions run against a real host, production-scale timing and the legal/docs reviews are outside what this workstation can prove.

---

_Verified: 2026-11-14T23:05:48Z_
_Verifier: the agent (gsd-verifier)_
