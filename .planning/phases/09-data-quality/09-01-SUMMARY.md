---
phase: 09-data-quality
plan: 01
subsystem: referential
tags: [handicap-families, csv, seed, admin-cli, data-quality]

requires:
  - phase: 03-referential-api
    provides: criteria.handicap_families / accessibility_filters.handicap_families columns and the family= search filter
provides:
  - "data/referential/families.csv: reviewed families for 19 base criteria, 4 option overrides and 52 filters"
  - "application/referential/families.py: load_families, apply_families (explicit row, option inheritance, group union), audit_families"
  - "seed() and `admin families sync` share apply_families; `admin families audit` is the DATA-01 gate"
  - "`criterion add --family` creates a family-compliant criterion"
affects: [09-02, 09-03, search-quality]

actuals:
  tokens: 8498
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Reviewed CSV as the single source for a referential attribute, validated against a domain tuple before any write"
    - "Sync fills only empty rows unless --force; an audit command fails the runbook step instead of a silent regression"

key-files:
  created:
    - data/referential/families.csv
    - src/letmegetin/application/referential/families.py
    - tests/unit/test_families.py
  modified:
    - src/letmegetin/seed.py
    - src/letmegetin/admin.py
    - src/letmegetin/application/referential/admin.py
    - src/letmegetin/domain/referential/repositories.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - tests/unit/test_seed.py
    - tests/integration/test_seed_vocabulary.py
    - tests/integration/test_admin_cli.py
    - README.md
    - docs/deploy.md

key-decisions:
  - "Family assignment lives in data/referential/families.csv, not code branches: all 75 rows are reviewable in one diff."
  - "apply_families is shared by seed() and `admin families sync`, so a fresh DB and the live dev/prod DBs converge through one code path."
  - "Options inherit their parent and a group carries the union of its children, so no tree node is family-less."
  - "sync only fills empty families unless --force, so an operator's `criterion families` edit is never reverted."
  - "The family filter drives search results, so families are assigned from what the criterion informs about, never to widen matching."

patterns-established:
  - "Audit gate: a read-only CLI command that exits 1 naming each offending slug (same shape as a health check)."
  - "Loader validating every CSV value against a domain tuple and naming the slug + value on failure."

requirements-completed: [DATA-01]

coverage:
  - id: D1
    description: "Every criterion (19 base, their options, 4 groups) and all 52 filters carry at least one handicap family after the seed"
    requirement: DATA-01
    verification:
      - kind: integration
        ref: "tests/integration/test_seed_vocabulary.py#test_seed_loads_vocabulary_without_polluting_criteria"
        status: pass
      - kind: other
        ref: "uv run python -m letmegetin.seed && uv run python -m letmegetin.admin families audit (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "`admin families sync` fills empty rows from the reviewed CSV; `admin families audit` exits 1 naming every slug without a family"
    requirement: DATA-01
    verification:
      - kind: integration
        ref: "tests/integration/test_admin_cli.py#test_families_sync_then_audit_passes"
        status: pass
      - kind: integration
        ref: "tests/integration/test_admin_cli.py#test_families_audit_names_a_criterion_that_lost_its_families"
        status: pass
    human_judgment: false
  - id: D3
    description: "`criterion add --family` creates a family-compliant criterion at creation time"
    requirement: DATA-01
    verification:
      - kind: integration
        ref: "tests/integration/test_admin_cli.py#test_criterion_add_accepts_families"
        status: pass
    human_judgment: false
  - id: D4
    description: "Live dev and prod hosts run `families sync` then `families audit` (exit 0) after the referential deploy"
    requirement: DATA-01
    verification: []
    human_judgment: true
    rationale: "The host run is an operator action against the deployed database; it cannot be exercised from CI and is recorded as the end-of-phase human check."

duration: 30min
completed: 2026-11-05
status: complete
---

# Phase 9 Plan 01: Handicap families Summary

**Every criterion and every accessibility filter now carries at least one of `moteur`/`auditif`/`visuel`/`mental`, sourced from one reviewed CSV, with a sync and an audit command.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-11-05
- **Tasks:** 2
- **Files modified:** 14 (3 created)

## Accomplishments

- `data/referential/families.csv` assigns families to 19 base criteria, 4 option overrides and 52 filters (75 rows, all slugs verified against the database).
- `application/referential/families.py` loads and validates the CSV (`DomainError` naming slug + value), writes explicit rows, lets options inherit their parent, and gives each group the union of its children in canonical `HANDICAP_FAMILIES` order.
- `seed()` and `admin families sync` share `apply_families`; a second seed run reports `families=0/0` and writes nothing.
- `admin families audit` exits `1` listing every slug without a family; `admin families sync|--force` is the fill path.
- `criterion add --family` keeps a CLI-created criterion compliant at creation time.
- The `family=` search filter (`PlaceRepository.list_near`) now has data to match, and `GET /api/v1/filters` / grids return non-empty `handicap_families`.

## Task Commits

Both tasks are one logical change (the data file, its use case and its CLI), committed as one plan commit per the repo rule:

1. **Task 1 + Task 2** - `0b57c1f` (feat) — `LET-33 feat(referential): assign handicap families to criteria and filters`

## Files Created/Modified

- `data/referential/families.csv` — reviewed families (`slug;families`, `|`-separated).
- `src/letmegetin/application/referential/families.py` — `load_families`, `apply_families`, `audit_families`, `FamiliesReport`.
- `src/letmegetin/domain/referential/repositories.py` — `FilterRepository.list_all()` + `update_families()`.
- `src/letmegetin/infrastructure/persistence/repositories.py` — implementations of the two new filter methods.
- `src/letmegetin/application/referential/admin.py` — `add_criterion(..., families=...)`.
- `src/letmegetin/seed.py` — applies families between the mapping load and `rebuild_category_grids`; prints `families=<n>/<n>`.
- `src/letmegetin/admin.py` — `families sync` / `families audit`, `criterion add --family`.
- `tests/unit/test_families.py` — 12 cases (CSV parsing, explicit rows, inheritance, option override, group union, overwrite semantics, idempotency, unknown slug, audit ordering).
- `tests/unit/test_seed.py` — fixture stubs `apply_families`/`load_families` (fake session cannot run the repositories).
- `tests/integration/test_seed_vocabulary.py` — asserts 0 criteria and 0 filters with empty families after the seed.
- `tests/integration/test_admin_cli.py` — sync→audit pass, blanked criterion named with exit 1, `criterion add --family`.
- `tests/integration/test_places_import.py` — added `ORDER BY c.position` to an assertion that relied on physical row order (see Deviation 5).
- `README.md`, `docs/deploy.md` — operator documentation for the sync→audit step.

## Verification (real output)

```
$ uv run python -m letmegetin.seed
seed ok: categories=158 base_criteria=19 vocabulary_created=0 vocabulary_skipped=182 mapping=158 families=23/52 referential_version=155

$ uv run python -m letmegetin.seed          # idempotent
seed ok: categories=158 base_criteria=19 vocabulary_created=0 vocabulary_skipped=182 mapping=158 families=0/0 referential_version=156

$ uv run python -m letmegetin.admin families sync
families sync: criteria=0 filters=0 inherited=0 unchanged=75

$ uv run python -m letmegetin.admin families audit; echo exit=$?
families ok: every criterion and filter has at least one family
exit=0

select count(*) from criteria where handicap_families='{}'            -> 0
select count(*) from accessibility_filters where handicap_families='{}' -> 0
```

Group unions after the seed: `entree=moteur`, `circulation=moteur`, `exterieur=moteur|visuel`, `services-et-equipements=moteur|auditif|visuel|mental`.

```
$ uv run ruff check .        -> All checks passed!
$ uv run mypy                -> Success: no issues found in 70 source files
$ uv run bandit -r src -c pyproject.toml -> 0 issues (Medium 0, High 0)
$ uv run pytest -q --cov=letmegetin --cov-branch --cov-fail-under=85
208 passed, 1 warning in 31.36s — Total coverage: 93.02%
```

## Decisions Made

- Family data is a reviewed CSV, not code branches; the use case is shared by seed and CLI so dev and prod converge identically.
- `sync` fills only empty rows unless `--force` (T-09-02): an operator edit survives a routine sync.
- The per-slug validation helper lives in `families.py` (not reused from `admin._validated_families`) because the plan requires the error to name the slug *and* the value; the canonical ordering rule is identical.
- `audit` runs its own session (`bump=False`, no commit) instead of `_run_admin`, because it must never write and must exit 1 with the slug list.

## Deviations from Plan

1. **[Instruction conflict] Committed on `main`, not on a `LET-33-…` branch.** The plan's `<output>` said to work on a branch, but the execution directive states GSD runs with `branching_strategy: none`; no branch was created.
2. **[Implementation detail] `_validated` duplicated in `families.py`** to satisfy "raise `DomainError` naming slug and value" (the existing `_validated_families` has no slug in its message). Ordering behaviour is identical.
3. **[Test fixture] `tests/unit/test_seed.py` now stubs `apply_families` and `load_families`**, because the fake session cannot run the SQLAlchemy repositories; this is the blocker the plan already listed in `files_modified`.
4. **[Formatting] Ruff's pre-commit formatter reflowed `families.py`** before the commit; no behavioural change.
5. **[Rule 1 — Bug] `test_places_import.py` asserted row order without `ORDER BY`.** Writing `handicap_families` updates the `criteria` heap, which changed the physical order returned by that SELECT and made the test fail after the seed. Fixed with `ORDER BY c.position` in the test query — the assertion's intent — so wave 2's importer work starts from a deterministic test.

**Total deviations:** 5 (1 instruction conflict, 1 small duplication, 1 planned test adaptation, 1 formatting, 1 ordering bug in an existing test).
**Impact on plan:** none on scope or acceptance; the ordering fix makes an existing test deterministic.

## Issues Encountered

None. `families sync` bumps `referential_version` through the shared `_run_admin` path even when it writes nothing; the data itself is idempotent (`criteria=0 filters=0`), which is what the plan's idempotency claim covers.

## Next Phase Readiness

- Wave 2 (`09-02`, DATA-02) can start: it depends only on schema head 0008 and does not touch the families file.
- Wave 3 (`09-03`) reuses nothing from this plan except the CLI conventions (`bump=False` for read-only reports).
- Remaining human step: after the referential deploy, run `families sync` then `families audit` on the dev and prod hosts (end-of-phase check).
- `data/referential/acceslibre_categories.csv` was not touched, as required.

## Self-Check: PASSED

- `data/referential/families.csv` — FOUND
- `src/letmegetin/application/referential/families.py` — FOUND
- `tests/unit/test_families.py` — FOUND
- commit `0b57c1f` — FOUND (ancestor of HEAD)

---
*Phase: 09-data-quality*
*Completed: 2026-11-05*
