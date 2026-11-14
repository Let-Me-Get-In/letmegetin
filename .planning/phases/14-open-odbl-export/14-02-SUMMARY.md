---
phase: 14-open-odbl-export
plan: 02
subsystem: places
tags: [odbl, export, zip, csv, mvcc, watermark, retention, licensing, attribution]

# Dependency graph
requires:
  - phase: 14-open-odbl-export
    plan: 01
    provides: export_event journal, safe_seq(), the place-write choke-point appends
  - phase: 12-licence-provenance
    provides: source_license columns, can_redistribute and its SQL twins, reviewed licence CSVs
provides:
  - letmegetin-admin export odbl --out DIR [--delta | --since seq|date]
  - snapshot ZIP of seven entries (places, categories, criteria, answers, aliases, ATTRIBUTION, manifest)
  - merged-answer remap with the deterministic winner order, losers counted per source+licence
  - latest.json (snapshot, watermark, retention_floor_seq, deltas[]) written atomically under flock
  - retention pruning of export_event and of the delta ZIPs a new snapshot subsumes
  - reviewed licence.attribution_text (migration 0013) rendered into ATTRIBUTION.txt
affects: [14-03 serving routes, 14-04 public-api docs, 14-05 export timer]

actuals:
  tokens: 22589
  tasks: 3
  commits: 3
  plan_head_before: 264c01445cf0a4c895a3fb48e17edcd93197420d
  plan_head_after: 9ee6423a31b34a2f3b2c7cbc48beef9e7502947e

tech-stack:
  added: []
  patterns:
    - "One REPEATABLE READ transaction: safe_seq() is its FIRST statement, so the boundary and the streamed rows share one snapshot (B5)"
    - "Rank over the full exportable population, then filter by the window: a delta picks the same winner the snapshot did (W4, B7)"
    - "A correlated subquery inside two nested EXISTS needs .correlate(cte); auto-correlation only looks one level out"
    - "Watermark advances only after os.replace + fsync of the delta ZIP, inside the flock that read latest.json (D-10)"
    - "Retention deletes by seq only (export_event has no FK to place), after the replacing snapshot is on disk (D-15)"

key-files:
  created:
    - src/letmegetin/domain/places/export_plan.py
    - src/letmegetin/application/places/export.py
    - src/letmegetin/application/places/attribution.py
    - migrations/versions/0013_licence_attribution_text.py
    - tests/unit/application/places/test_export.py
    - tests/functional/places/test_export.py
  modified:
    - src/letmegetin/infrastructure/persistence/export_repositories.py
    - src/letmegetin/domain/places/export.py
    - src/letmegetin/domain/referential/entities.py
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/application/referential/licences.py
    - src/letmegetin/infrastructure/persistence/licence_repositories.py
    - src/letmegetin/admin.py

key-decisions:
  - "A withheld answer does not compete in the ranking: the answer-licence filter sits INSIDE the ranked CTE, before row_number, so a redistributable merged answer can win where the canonical's answer is withheld."
  - "The answer-event EXISTS correlates the event place's canonical id (COALESCE after the merge) and matches payload->>'criterion_slug' to the ranked criterion — never entity_id to the criterion (W7)."
  - "A merge in the window re-emits every winner of the merged-into canonical (deliberate superset, B7); replay is an idempotent upsert, so over-emitting is safe and under-emitting is not."
  - "Attribution lists the (source, source_license) pairs the exported rows actually carry, then reads legal name and sentence from licences.csv — the write path already resolved source→licence, so re-reading source_licences.csv would be a second, divergent lookup."
  - "After a snapshot the deltas[] list is empty, so 'delete delta ZIPs whose to_seq <= snapshot seq' and 'delete unlisted orphans' collapse into one rule: keep only what latest.json lists."
  - "ZIP names carry microseconds (export-...-full.zip, delta-...zip, export-...-since-<seq>.zip): two runs in the same second were overwriting each other's archive."
  - "The use case reads the boundary and rows through one session and prunes in the same transaction; the caller must commit for the prune to land (the admin runner does)."

patterns-established:
  - "A streaming read returns the row dataclasses the CSV writer consumes, so the application layer never sees an ORM row."
  - "The formula guard is applied by column index from a per-file free-text allow-list, computed once per file, never per cell (F4)."

requirements-completed: [EXP-01, EXP-02]

coverage:
  - id: D1
    description: "export odbl writes a ZIP of exactly the seven agreed entries; each CSV is UTF-8, comma-separated, RFC 4180 quoted, header row, no BOM; manifest carries schema_version, generated_at, referential_version, per-file counts, the three exclusion counters and attribution_ref"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "tests/functional/places/test_export.py#test_snapshot_zip_carries_the_seven_files_and_only_canonical_places"
        status: pass
      - kind: unit
        ref: "tests/unit/application/places/test_export.py (RFC 4180 round-trip, manifest keys, header untouched by the guard)"
        status: pass
    human_judgment: false
  - id: D2
    description: "only canonical places export; a merged place appears only in aliases.csv, its answers remapped onto the canonical id with the deterministic winner order and the losers counted per source+licence"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "test_snapshot_zip_carries_the_seven_files_and_only_canonical_places (canonical wins, merged answer remapped, loser counted)"
        status: pass
      - kind: unit
        ref: "test_answer_precedence_prefers_the_canonical_place_then_the_newest_then_the_highest_ids"
        status: pass
    human_judgment: false
  - id: D3
    description: "an answer leaves only when its own licence AND its canonical place allow open_export; the withheld answer is absent and counted, place-withheld answers are counted apart, and the three populations reconcile with the canonical total"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "test_the_exported_plus_excluded_plus_withheld_answers_reconcile (exported + excluded + withheld == canonical total)"
        status: pass
      - kind: unit
        ref: "test_a_withheld_answer_is_absent_from_the_stream_and_counted_by_source_and_licence"
        status: pass
    human_judgment: false
  - id: D4
    description: "latest.json carries snapshot {name, seq}, watermark, retention_floor_seq and deltas[]; a delta publishes only watermark < seq <= safe_seq(), advances the watermark only after the ZIP is fsynced, and a failed run leaves it untouched"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "test_a_delta_publishes_only_the_window_and_moves_the_watermark; test_a_failed_delta_leaves_the_watermark_untouched"
        status: pass
      - kind: functional
        ref: "test_a_delta_never_skips_an_event_from_an_in_flight_transaction (safe_seq excludes, then includes after commit)"
        status: pass
    human_judgment: false
  - id: D5
    description: "--since replays cumulatively from a seq or an ISO date, leaves latest.json untouched, and is refused below retention_floor_seq naming the floor and the snapshot to restart from"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "test_a_catch_up_replays_since_the_snapshot_and_refuses_below_the_floor"
        status: pass
    human_judgment: false
  - id: D6
    description: "retention prunes export_event to the PREVIOUS snapshot boundary, removes the delta ZIPs the new snapshot subsumes and unlisted orphans, keeps the snapshot ZIPs, and a failed snapshot prunes nothing"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "test_retention_prunes_to_the_previous_snapshot_and_removes_old_deltas; test_a_failed_snapshot_prunes_nothing"
        status: pass
    human_judgment: false
  - id: D7
    description: "ATTRIBUTION.txt lists only the sources actually exported, with their licences.csv legal name and reviewed attribution_text sentence, the Produced Works sentence and the forward-looking sentence, repeated verbatim in manifest.attribution"
    requirement: EXP-02
    verification:
      - kind: functional
        ref: "test_snapshot_zip_carries_the_seven_files_and_only_canonical_places (AccesLibre + Etalab name + sentence; no OSM/Overture; equals manifest)"
        status: pass
      - kind: unit
        ref: "test_render_source_line_appends_the_reviewed_sentence_of_its_licence; test_render_source_line_omits_a_licence_sentence_it_does_not_have"
        status: pass
    human_judgment: false
  - id: D8
    description: "the three reviewed attribution_text sentences (already on main in licences.csv) are the legal wording a partner archive will carry"
    requirement: EXP-02
    verification:
      - kind: other
        ref: "data/referential/licences.csv, rendered in ATTRIBUTION.txt by the functional test"
        status: pass
    human_judgment: true
    rationale: "Whether each sentence is the wording its licence requires is a legal judgement no test asserts. Values shipped, for operator review: lov2 = « Source » : nom du producteur et date de dernière mise à jour. / odbl = © contributeurs — base de données sous ODbL 1.0 : toute base dérivée reste sous ODbL (partage à l'identique) et doit rester ouverte tant qu'elle est utilisée. / cdla = Contains data provided by the data provider(s) under CDLA-Permissive 2.0."

# Metrics
duration: 80min
completed: 2026-11-14
status: complete
---

# Phase 14 Plan 02: ODbL export ZIP, watermark delta and retention Summary

**`letmegetin-admin export odbl` now writes the partner ZIP — canonical places, a remapped answer per (canonical place, criterion) filtered by the reviewed licence matrix, aliases as the tombstone stream, a present-sources ATTRIBUTION carrying each licence's reviewed sentence — plus `latest.json` and an MVCC-bounded delta, and prunes the journal only once the snapshot replacing its boundary is on disk.**

## Performance

- **Duration:** ~80 min
- **Tasks:** 3 executed (Task 1 = TDD unit slice, Tasks 2–3 static + behavioural gates)
- **Files modified/created:** 13 (6 created, 7 modified)

## Accomplishments

- **Seven-entry ZIP, streamed.** `places.csv`, `categories.csv`, `criteria.csv`, `answers.csv`, `aliases.csv`, `ATTRIBUTION.txt`, `manifest.json`. Every CSV is written through `csv.writer` (`lineterminator="\n"`) into `zipfile` entries opened with `force_zip64`, fed row by row from an async generator — no 1.7M-answer list is ever materialised.
- **One snapshot, one boundary.** `export_odbl` sets `REPEATABLE READ` on the session connection and calls `safe_seq()` as the first statement; every stream afterwards reads that same snapshot, so the delta window and the rows it publishes cannot disagree (B5).
- **The answer stream is the hard part.** A `ranked_answers` CTE joins `place_accessibility → place → the effective canonical place → criteria`, filters on the canonical place's licence **and** the answer's own licence, then picks `rn = 1` by `(place_id = canonical) DESC, recorded_at DESC, place_id DESC, criterion_id DESC`. Merged answers land under the canonical id; losers and withheld answers are counted per source+licence. The window filter runs *after* ranking, as an `EXISTS` on `export_event` matching `payload->>'criterion_slug'` to the ranked criterion and the event place's canonical id to the ranked canonical id.
- **A correlation bug worth recording:** the nested `entity_id IN (SELECT place.id WHERE canonical_id = ranked.canonical_id)` auto-correlated `ranked_answers` into the *inner* select, so the merge branch matched almost every row and every winner was re-emitted in every delta. Fixed with `.correlate(ranked)`; the SQL now reads `IN (SELECT place.id FROM place WHERE place.canonical_id = ranked_answers.canonical_id)`.
- **`latest.json`** carries `{schema_version, generated_at, referential_version, snapshot {name, seq}, watermark, retention_floor_seq, deltas[] {name, from_seq, to_seq}, attribution_ref}`; written to a temp file, fsynced, `os.replace`d, directory fsynced — all inside `flock(out/latest.json.lock)`. The watermark moves only after the delta ZIP itself is fsynced and replaced.
- **Retention** deletes `export_event` up to the *previous* snapshot seq and removes every `delta-*.zip` the new snapshot did not list (which is all of them: a new snapshot starts a fresh chain), plus orphan `delta-*.zip` files. A snapshot that raises before its ZIP is complete prunes nothing and leaves no temp file behind.
- **Attribution** reads the (source, licence) pairs the exported rows actually carry, then `licences.csv` for the legal name and the reviewed `attribution_text`; the text is repeated verbatim in `manifest.attribution`. No per-row attribution column, no hard-coded OSM/Overture line.
- **The licence schema behind it** is now full-stack: `Licence.attribution_text`, `LicenceModel.attribution_text` (nullable), migration `0013` (`down_revision "0012"`, add column, no backfill), `load_licences` reading the fifth CSV column, and both repository reads/writes carrying it.

## Task Commits

Each task was committed atomically:

1. **Task 1: Reviewed attribution_text schema + pure export plan** — `107c7ef` (feat)
2. **Task 2: Bulk read, snapshot/delta/catch-up use case, retention** — `f83e78b` (feat)
3. **Task 3: `export odbl` CLI + functional ZIP/delta/remap/retention tests** — `9ee6423` (feat)

**Plan metadata:** committed separately after this file.

## Verification (real output)

- `uv run alembic upgrade head` (test DB) → `Running upgrade 0012 -> 0013, reviewed per-licence attribution sentence for the open export`; `uv run alembic current` → `0013 (head)`; `downgrade 0012` then `upgrade head` round-trips.
- `uv run pytest tests/unit/application/places/test_export.py -m unit -x` → **14 passed**.
- `uv run pytest tests/functional/places/test_export.py -m functional -x` → **9 passed** (1 third-party `httpx` deprecation warning).
- `uv run pytest -q` → **453 passed, 1 warning** in 128 s (was 430 before this plan).
- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `163 files already formatted`.
- `uv run mypy` → `Success: no issues found in 86 source files`.
- `uv run bandit -r src -c pyproject.toml` → `Total issues: 0` (Low 0, Medium 0, High 0).
- `node .gitnexus/run.cjs analyze --index-only` (index was stale at `46723b5`) → `3 841 nodes | 7 570 edges`; `detect-changes --scope all` → `Changes: 6 files, 31 symbols`, `Risk level: high`, affected flows are the new export path plus the CLI callback — no pre-existing flow regressed.

All archive assertions open the produced ZIP with `zipfile` and parse every CSV with `csv.DictReader`; none asserts on file existence alone.

## Decisions Made

- **Filter-then-rank.** A withheld answer is excluded *inside* the ranked CTE, so it neither wins nor blocks a redistributable merged answer. The full-population ranking of W4 therefore means the full *exportable* population.
- **Merge superset is deliberate.** A merge event in the window re-emits every winner of the merged-into canonical, even when no answer event fired; the functional test asserts both that superset and that an untouched winner whose place saw no merge is absent.
- **Delta ZIP names are `delta-<stamp>.zip`** (not `export-<stamp>-delta.zip`), because the plan's own orphan rule and D-15 both speak of `delta-*.zip`. Snapshot and catch-up keep `export-…-full.zip` / `export-…-since-<seq>.zip`.
- **Microsecond timestamps in ZIP names.** Two exports in the same second produced the same filename and the second silently overwrote the first — caught by the safe_seq test, fixed in `_write_zip`'s callers.
- **The port owns the isolation level.** `begin_repeatable_read()` sits on `ExportPlanRepository` rather than in the CLI, so the application layer stays free of SQLAlchemy and the snapshot is owned by the use case that also streams it.
- **The caller commits.** `delete_up_to` runs in the export's transaction; the admin runner's commit is what makes the prune durable. A caller that only reads would roll the prune back (this bit the functional helper before it committed).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The port needed two methods the plan did not list**
- **Found during:** Task 2 (mypy gate)
- **Issue:** `delete_up_to` and `seq_at_or_before` live on the SQLAlchemy event repository, but `export_odbl` types its second argument as the domain `ExportEventRepository`; without them on the port, the application layer would have to import infrastructure.
- **Fix:** added both (plus docstrings) to `domain/places/export.py`; the file is not in the plan's `files_modified`.
- **Files modified:** `src/letmegetin/domain/places/export.py`
- **Verification:** `uv run mypy` → no issues in 86 source files.
- **Committed in:** `f83e78b`

**2. [Rule 3 - Blocking] A failed pre-commit mypy on the staged tree**
- **Found during:** Task 2 commit
- **Issue:** `export_plan.py` (carrying `begin_repeatable_read` on the Protocol) was left unstaged, so the hook checked a tree where the use case called a method the protocol lacked.
- **Fix:** staged the port change with the task that needs it; no `--no-verify`.
- **Files modified:** `src/letmegetin/domain/places/export_plan.py`
- **Verification:** commit `f83e78b` landed with every hook passing.
- **Committed in:** `f83e78b`

### Plan adjustments (documented, not defects)

**3. Streaming uses `AsyncSession.stream()`, not keyset pages.** The ranked answer CTE cannot be keyset-paginated without recomputing the ranking for every page (quadratic over 1.7M answers), so both streams use a server-side cursor with `yield_per=1000`. The requirement — bounded memory, never a full list — is met.
**4. Attribution derives the source list from each row's own `source_license`** instead of re-reading `source_licences.csv`: the write path already resolved that mapping at write time (LIC-05), and a second lookup could diverge from the licence actually stamped on the row. Legal name and sentence still come from `licences.csv`.
**5. `serialise_rows(header, rows, file)`** takes the header and the file name so the free-text allow-list is per file; the plan sketched `serialise_rows(rows)`.
**6. `licences.csv` already carried `attribution_text`** on `main` (commit `02445b9`, the reviewed values). This plan shipped the schema and code behind it; the CSV itself needed no change, so the three sentences are flagged `human_judgment` here rather than in a new CSV diff.

---

**Total deviations:** 2 auto-fixed (2 blocking), 4 documented plan adjustments.
**Impact on plan:** No behavioural scope change; typing, naming and streaming mechanics only.

## Threat Flags

None new. `--out` is the only filesystem path an operator supplies; nothing is written outside it, and the export adds no network surface (the read-only routes are 14-03). T-14-04 (answer filter), T-14-12 (formula guard), T-14-16 (retention) and T-14-17 (safe_seq) each have a functional or unit test above.

## Known Stubs

None. Every file the ZIP promises carries real rows; the only intentionally absent data is a withheld row, and that absence is counted in the manifest by design (D-03).

## Issues Encountered

- The nested-EXISTS correlation bug (see Accomplishments) was caught by the delta functional test, not by review: every delta was re-emitting every winner. The unit tests could not have found it — it is a SQL correlation fact.
- `retention` prunes by `seq` alone and `export_event` has no FK, so the functional retention tests delete events belonging to any suite that ran earlier in the same database. Every suite seeds its own events per test, so this is safe today; a suite that reads another suite's journal would break.

## User Setup Required

`uv run alembic upgrade head` on each environment (migration 0013 adds `licence.attribution_text`). After that, `letmegetin-admin licences sync` fills the column from `data/referential/licences.csv`; nothing reads it from the database yet (the export reads the CSV directly).

## Next Phase Readiness

- **14-03 (serving):** `latest.json` is written next to the ZIPs and a `{name}.zip` route only needs to join `--out` with a name from `deltas[]`/`snapshot`. The directory also holds `latest.json.lock` and transient dotfile temps — do not serve or index them.
- **14-04 (public contract):** the manifest keys and the seven file names are frozen here; `application/places/attribution.py` exposes `PRODUCED_WORKS_SENTENCE` and `FORWARD_LOOKING_SENTENCE` for a docs test to import rather than copy. "Origin id" per file: places → (source, source_id); answers → (place_id, criterion_slug); categories/criteria → slug.
- **14-05 (timer/ops):** weekly `export odbl --out <served dir>` and daily `export odbl --delta --out <served dir>`; the flock only serialises one host, which is the D-12 design. A delta with no `latest.json` fails loudly rather than inventing a baseline.
- **Any later caller of `export_odbl`** must commit the session, or retention silently rolls back.
- `--since <date>` resolves through `export_event.occurred_at <= end of that ISO day` (the column is a naive timestamp), so the boundary is the last event of that day in server time.

---

## Self-Check: PASSED
