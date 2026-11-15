---
phase: 15-acceslibre-round-trip
plan: 06
subsystem: referential
tags: [dual-licence, lov2-partner, contribution-terms, licence-gate, reviewed-data, feed]

# Dependency graph
requires:
  - phase: 12-licence-provenance
    provides: the reviewed licence catalogue, matrix and source mapping, resolved at write time
  - phase: 14-open-odbl-export
    provides: the snapshot writer and the licence-gated streams
  - phase: 15-acceslibre-round-trip
    provides: the lov2_partner projection and feed (15-04), the push stream gate (15-05)
provides:
  - the `dual` licence slug (lov2 + ODbL) with a reviewed attribution_text naming both
  - `user -> dual` in source_licences.csv, so new contributions are shippable to lov2_partner
  - `dual -> lov2_partner/open_export/osm` rows in the reviewed matrix
  - a functional proof that a new user answer is stamped `dual` and appears in the feed
affects: [16-osm-export]

actuals:
  tokens: 2511
  tasks: 1
  commits: 1
  plan_head_before: ebaf7229d48ffb31c3e2b1eea8613dc43844c5b2
  plan_head_after: aef5f1cdcaa0886105f0f89386cd27b773e0eb9c

tech-stack:
  added: []
  patterns:
    - "the licence change is three reviewed CSV rows: no branch, no migration, no code path"
    - "the feed assertion reads answers.csv of a real snapshot, not a matrix query"

key-files:
  created:
    - tests/functional/test_licence_migration.py
  modified:
    - data/referential/licences.csv
    - data/referential/licence_destinations.csv
    - data/referential/source_licences.csv
    - docs/public-api.md
    - tests/functional/places/test_provenance_write.py
    - tests/functional/referential/test_admin_cli.py
    - tests/integration/referential/test_seed_vocabulary.py

key-decisions:
  - "Contributor terms, 2026-11-15: `new-only` — dual applies to new contributions only; existing odbl user rows are never re-licensed, so Task 3 and migration 0016 do not exist."
  - "The lov2 feed and the push therefore carry only post-change `dual` contributions; historical `odbl` user answers stay withheld from `lov2_partner` (INFO-11). The phase is not 'all owned rows flow back'."
  - "`dual` names both licences in its attribution_text (D-02) and keeps the share-alike obligation, so the ODbL open export keeps its guarantee."
  - "The test file keeps the plan's path `test_licence_migration.py`; it holds only the feed assertion because the re-stamp test it was to gain was cancelled with Task 3."

requirements-completed: [PART-01, PART-02]

coverage:
  - id: D1
    description: "`dual` joins the catalogue with an attribution_text naming lov2 and ODbL; `user -> dual`; `dual -> lov2_partner/open_export/osm = true`; sync and audit exit 0"
    requirement: PART-01
    verification:
      - kind: other
        ref: "uv run python -m letmegetin.admin licences sync && uv run python -m letmegetin.admin licences audit"
        status: pass
    human_judgment: false
  - id: D2
    description: "A NEW user contribution is stamped `dual` at write time and appears in answers.csv of a `--destination lov2_partner` snapshot, while odbl and cdla answers do not; ATTRIBUTION carries the dual line naming both licences"
    requirement: PART-01
    verification:
      - kind: functional
        ref: "tests/functional/test_licence_migration.py#test_new_user_answer_is_dual_and_reaches_the_lov2_feed"
        status: pass
    human_judgment: false
  - id: D3
    description: "The contributor-terms decision is recorded and existing `odbl` user rows are left alone: no migration 0016, no re-stamp"
    requirement: PART-02
    human_judgment: true
    rationale: "The decision is a legal/product call taken by the operator (`new-only`), not something a test can assert. The feed consequence is covered by D2; the withheld historical rows are the intended outcome, recorded below."

duration: 23min
completed: 2026-11-15
status: complete
---

# Phase 15 Plan 06: Dual licence and the contributor-terms decision Summary

**Contributions are now shippable to a lov2 partner: `user` writes are stamped `dual` (lov2 + ODbL), the reviewed matrix lets `dual` reach `lov2_partner`, and a functional test proves a new user answer lands in the feed's `answers.csv` — while historical `odbl` answers stay withheld by the operator's `new-only` decision.**

## Performance

- **Duration:** ~23 min
- **Completed:** 2026-11-15
- **Tasks:** 1 executed, 1 decision resolved by the operator, 1 not executed by that decision
- **Files modified:** 8 (1 created)

## The decision (verbatim)

**Task 2 `checkpoint:decision gate="blocking-human"` — resolved by the operator on 2026-11-15:**

> **Select: new-only** — "dual for new contributions only. No retroactive re-licensing; existing rows keep the ODbL grant contributors made."

Consequences applied exactly:

- Task 1 ran: the `dual` rows, `user -> dual`, `dual -> lov2_partner`, sync/audit/feed assertion. D-01/D-02 stay locked.
- **Task 3 was NOT executed.** No `migrations/versions/0016_dual_licence_restamp.py` exists. Existing `place_accessibility.source_license = 'odbl'` rows for `source='user'` are unchanged.
- Because existing rows stay `odbl` (`odbl × lov2_partner = false`), **the lov2 feed and the push carry only post-change `dual` contributions — never "all owned rows"** (INFO-11). The partner feed is a freshness mirror for historical user answers and a contribution loop only for new ones.
- A contribution-terms clause will be added separately; that is why re-licensing is not done here.

## Accomplishments

- **`data/referential/licences.csv`** gains `dual` — "Licence Ouverte v2.0 (Etalab 2.0) + Open Database License 1.0", obligations `attribution|share_alike|keep_open`, and an `attribution_text` that names both licences (with both URLs) and restates the ODbL share-alike. The single `url` column points at the Etalab page; the ODbL URL lives in the text (D-02).
- **`data/referential/licence_destinations.csv`** gains `dual -> lov2_partner=true`, `dual -> open_export=true`, `dual -> osm=true`. `acceslibre;lov2`, `odbl;lov2_partner=false` and `cdla;lov2_partner=false` are untouched (D-03, LIC-03).
- **`data/referential/source_licences.csv`**: `user;odbl;2026-10-26` becomes `user;dual;2026-11-15`, so `_source_licence('user')` stamps new writes `dual`.
- **`licences sync`** reports `created=4 updated=1 unchanged=13` (the dual catalogue row, its three matrix rows, and the moved source row); **`licences audit`** exits 0 with "every licence has a full matrix and every row resolves".
- **`tests/functional/test_licence_migration.py`** (real PostGIS, pinned `origin_id` rule): writes one `user` answer and one each under `odbl` and `cdla` sources, asserts the user row is stamped `dual`, exports `--destination lov2_partner`, and asserts the `dual` answer is present in `answers.csv` (field `entree_pmr`, `source_license=dual`) while the `odbl` and `cdla` answers are absent. ATTRIBUTION is asserted to carry the dual line naming both licences.
- **`docs/public-api.md`** names `dual` in the `source_license` slug list, which was a closed enumeration.

## Task Commits

1. **Task 1: The dual licence rows + sync + audit + feed assertion** — `aef5f1c` (feat)
2. **Task 2: Contributor-terms decision** — resolved by the operator as `new-only` (no commit; recorded here)
3. **Task 3: The re-stamp migration (0016)** — NOT EXECUTED, per the Task 2 decision

**Plan metadata:** the close-out commit carrying this SUMMARY and `deferred-items.md`.

## Verification (real output)

| Check | Command | Result |
|---|---|---|
| Licence sync | `uv run python -m letmegetin.admin licences sync` | `created=4 updated=1 unchanged=13` |
| Licence audit | `uv run python -m letmegetin.admin licences audit` | `licences ok: every licence has a full matrix and every row resolves` |
| Feed assertion | `uv run pytest tests/functional/test_licence_migration.py -m functional -x` | 1 passed |
| Migrations | `uv run alembic upgrade head` | no upgrade: head is `0015` (no 0016 by decision) |
| Full suite | `uv run pytest -q` | 592 passed in 163.54s |
| Lint / format | `uv run ruff check` / `ruff format --check` on touched files | All checks passed |
| Types | `uv run mypy` | Success: no issues found in 94 source files |
| Graph check | `node .gitnexus/run.cjs detect-changes --scope all` | 7 files, 6 symbols, risk low, 0 affected processes |

## Files Created/Modified

- `data/referential/licences.csv` — the `dual` catalogue row with its reviewed attribution_text.
- `data/referential/licence_destinations.csv` — three `dual` matrix rows.
- `data/referential/source_licences.csv` — `user -> dual` (effective 2026-11-15).
- `tests/functional/test_licence_migration.py` — the write-time stamp, the feed assertion, the ATTRIBUTION assertion.
- `docs/public-api.md` — `dual` added to the `source_license` slug list.
- `tests/functional/places/test_provenance_write.py`, `tests/functional/referential/test_admin_cli.py`, `tests/integration/referential/test_seed_vocabulary.py` — stale `user -> odbl` expectations updated to `dual`.

## Decisions Made

- **`new-only` closes the contributor-terms gate.** Existing ODbL grants are not re-licensed; the legal posture is preserved and the feed's historical coverage is consciously limited. A contribution-terms clause is a separate piece of work.
- **Both URLs are not in the `url` column.** A licence row has one URL; the Etalab page is the primary grant and the ODbL URL is named inside `attribution_text`, which is what D-02 asks the text to carry anyway.
- **The feed test lives at the plan's path.** `test_licence_migration.py` keeps its planned name even though the migration half was cancelled, so the plan's artifact is where a verifier looks; the module docstring says why the re-stamp test is absent.
- **The test pins the identifier rule** (`origin_id;VERIFIED`) rather than monkeypatching the loader — the same seam 15-04 used, and the reason the committed `blocked;UNVERIFIED` does not turn the assertion into a header-only feed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Three suites asserted the old `user -> odbl` mapping**
- **Found during:** Task 1 (full-suite run)
- **Issue:** `test_licences_sync_loads_the_reviewed_source_mapping` asserted `mapping["user"] == "odbl"`, `test_a_contribution_carries_the_user_licence_never_none` expected `source_license="odbl"`, and `test_seed_loads_the_reviewed_licence_data` asserted `mapping["user"] == "odbl"`. The reviewed data is now `dual`, so all three failed.
- **Fix:** the three expectations now read `dual`, derived from the same reviewed CSV the code reads.
- **Files modified:** the three test files above
- **Commit:** `aef5f1c`

**2. [Rule 1 - Bug] The public API doc enumerated a closed licence set without `dual`**
- **Found during:** Task 1
- **Issue:** `docs/public-api.md` said `source_license` is one of `lov2`, `odbl`, `cdla`; after this plan a `dual` row can appear in both the ODbL export and the partner feed.
- **Fix:** added `dual` to the enumeration.
- **Commit:** `aef5f1c`

### Deviations (recorded, not defects)

**3. [Deviation - Decision] Task 3 and migration 0016 do not exist**
- **Found during:** Task 2
- **Resolution:** the operator chose `new-only`; no re-stamp migration was written and no existing row moved. The high-severity threat T-15-11 (a silent re-licence of contributor data) has no artifact to mitigate. See "The decision" above for the feed consequence.

## Issues Encountered

- **`test_provenance` wipes the licence tables.** `test_backfill_resolves_every_source_from_reviewed_data` downgrades to `0010` and upgrades to `head`, recreating `licence`, `licence_destination` and `source_licence` empty. Running `test_acceslibre_push.py` after it in one session fails 8 tests for want of a matrix (they pass once `licences sync` repopulates it). This is pre-existing and out of scope; recorded in `deferred-items.md`. The full suite is green because `places/` collects before the suites that sync.
- **The `dual` test fixture syncs its own matrix**, so it is independent of that ordering.

## Threat Flags

None. The change adds reviewed data and one test; no new endpoint, auth path or file-access pattern. T-15-SC holds: no package was added.

## User Setup Required

None. No secret was read. The AccesLibre API key (`LETMEGETIN_ACCESLIBRE_API_KEY`, LET-130) remains outstanding for 15-05's deferred PATCH-contract check and does not affect this plan.

## Next Phase Readiness

- **The feed (15-04) and the push (15-05) widen by data alone**: `dual × lov2_partner = true` is the only new permission; neither use case keys on a licence name.
- **Known limit to carry into partner conversations:** historical user contributions stay `odbl` and out of `lov2_partner`. Only post-2026-11-15 contributions flow back. Say that, do not imply "all our data".
- **The contribution-terms clause** (a separate task) is what would ever unlock a re-stamp; until then `new-only` is the standing decision.
- **Phase 16 (OSM)** can reuse `dual -> osm=true`; the OSM attribution permission is still an ask in `15-PARTNER-ASK.md`.

---

## Self-Check: PASSED

- `data/referential/licences.csv` — `dual` row present, both licences named.
- `data/referential/licence_destinations.csv` — three `dual` rows; `odbl;lov2_partner=false` and `cdla;lov2_partner=false` intact.
- `data/referential/source_licences.csv` — `user;dual;2026-11-15`.
- `tests/functional/test_licence_migration.py` — FOUND, 1 passed.
- Commit `aef5f1c` — ancestor of HEAD; full suite 592 passed; ruff, ruff format and mypy clean.
- No `migrations/versions/0016_dual_licence_restamp.py` — correct per the `new-only` decision.

*Phase: 15-acceslibre-round-trip*
*Completed: 2026-11-15*

## Post-audit correction (2026-11-15)

The `new-only` decision was taken on the assumption that user answers already existed.
They do not: `place_accessibility where source='user'` = 0, `contribution` = 0,
`place where source='user'` = 0 on the dev database, and `source_licence` already maps
`user → dual` with `dual → lov2_partner` allowed.

So the consequence recorded above — "the feed carries only post-change `dual`
contributions, never all owned rows" — has **no effect today**: there are no owned rows
to leave behind, and every future contribution is stamped `dual` at write time. `new-only`
and a re-stamp are indistinguishable until the contributor terms ship (LET-131).
