---
phase: 02-referential-seed
verified: 2026-10-27T10:44:48Z
status: passed
score: 6/6 must-haves verified
covered_files: [".planning/phases/02-referential-seed/02-01-PLAN.md", ".planning/phases/02-referential-seed/02-01-SUMMARY.md", "migrations/versions/0002_referential_curation.py", "pyproject.toml", "src/letmegetin/admin.py", "src/letmegetin/application/referential/admin.py", "src/letmegetin/core/exceptions.py", "src/letmegetin/domain/referential/entities.py", "src/letmegetin/domain/referential/labels.py", "src/letmegetin/domain/referential/repositories.py", "src/letmegetin/infrastructure/persistence/mappers.py", "src/letmegetin/infrastructure/persistence/models.py", "src/letmegetin/infrastructure/persistence/repositories.py", "src/letmegetin/seed.py", "uv.lock"]
covered_digest: "v3:sha256:f851b52d05cf54be03da543c2881ce79cd07c8469d34384b8e3c8ea6e0986026"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 2: Referential & Seed Verification Report

**Phase Goal:** The API exposes categories, the criteria tree and filters from the reconstructed seed.
**Verified:** 2026-10-27T10:44:48Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | REF-04: the 182 flat labels live in `criterion_vocabulary`; none is inserted as a top-level criteria row; `criteria` holds only the category-1 grid. | ✓ VERIFIED | DB: `vocab=182 categories=158 criteria=61 is_default=19 cc_rows=0`; `tests/integration/test_seed_vocabulary.py` asserts `criteria == grid node count` and idempotent second seed; `seed.py` loads `criteria.json` only into `CriterionVocabularyModel`. |
| 2 | REF-05: the Typer CLI adds/edits categories, criteria and options, links/unlinks to categories, imports the vocabulary and sets fr/en/es/de/it labels. | ✓ VERIFIED | `python -m letmegetin.admin --help` lists `category`, `criterion`, `vocabulary`, `labels`, `link`, `unlink`; `tests/integration/test_admin_cli.py` exercises add/edit category, group/criterion/option add, `--default`/`--no-default`, link/unlink, three label setters and promote against real PostGIS (6 integration tests pass). |
| 3 | The default mapping is data: `criteria.is_default` (19 rows) plus `category_criteria.excluded`; per-category read resolves defaults − exclusions + includes and survives a re-seed. | ✓ VERIFIED | `repositories.list_for_category` computes `is_default − excluded ∪ included` then keeps ancestors and descendants; `test_unlink_default_criterion_survives_relisted_defaults` and `test_link_default_criterion_clears_the_exclusion` pin it; second `seed` leaves `cc_rows=0` and the counts unchanged. |
| 4 | REF-01/02/03: the existing reads still serve the full JSONB label map for categories, the per-category tree (including option nodes), filters and official labels, and a label can hold all five locales. | ✓ VERIFIED | Real DB read: 158 categories, tree roots 4 / depth 4 / 38 option nodes for `restaurant`, 52 filters, 15 other-information; `tests/unit/test_api.py::test_endpoints_return_full_label_maps` and `test_criteria_tree_exposes_description_and_option_nodes` pass a five-locale map through all four endpoints unchanged. |
| 5 | `alembic upgrade head` applies 0002 on a database at 0001 and `downgrade 0001` removes only the new table/column/index. | ✓ VERIFIED | Ran downgrade→upgrade: after downgrade `to_regclass('criterion_vocabulary')` null and 0 `is_default`/`excluded` columns; upgrade clean; `alembic current` = `0002 (head)`; `0002` drops only `excluded`, `is_default`, the slug index and the table. |
| 6 | Unit tests drive use cases through fakes; integration tests drive the CLI/seed through real PostGIS; quality gates and CI are green. | ✓ VERIFIED | `84 passed`, 97.49% line+branch (floor 85%); integration `6 passed`; ruff + format clean, mypy clean (35 files), bandit no issues; `gh pr checks 5` 6/6 pass, PR `CLEAN`. |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Deferred Items

None.

### Advisory (New Scope, Unevidenced)

None — initial verification, no new-scope findings.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `migrations/versions/0002_referential_curation.py` | `criterion_vocabulary`, `criteria.is_default`, `category_criteria.excluded` | ✓ VERIFIED | Revision `0002`, down_revision `0001`; creates table + unique slug index + both columns + backfill + one-shot `DELETE FROM category_criteria`; reversible. |
| `src/letmegetin/admin.py` | Typer CLI: category, criterion, vocabulary, labels, link, unlink | ✓ VERIFIED | All command groups present; `_run_admin` maps `DomainError` to stderr + exit 1; `__main__` guard works. |
| `src/letmegetin/application/referential/admin.py` | Write use cases | ✓ VERIFIED | `import_vocabulary`, `add/edit_category`, `add/edit_criterion`, `link/unlink`, `promote_vocabulary`, three label setters; no commit in this layer. |
| `src/letmegetin/domain/referential/labels.py` | `SUPPORTED_LOCALES`, `parse_label_pairs`, `normalize_label`, `merge_label` | ✓ VERIFIED | Pure module over `fr/en/es/de/it`; rejects unknown locale / missing separator. |
| `src/letmegetin/infrastructure/persistence/models.py` | `CriterionVocabularyModel`, `is_default`, `excluded` | ✓ VERIFIED | Mirrors 0002 column-for-column; JSONB label/description; FK `ON DELETE SET NULL`. |
| `tests/unit/test_admin.py` | Fake-repository use-case tests | ✓ VERIFIED | Covers duplicate slug, label merge/reparent, type validation, default/exclusion mapping, promote, errors, CLI exit paths. |
| `tests/integration/test_admin_cli.py` | CLI end-to-end against PostGIS | ✓ VERIFIED | 3 tests; skips cleanly without DB; asserts no SQL leaks. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `admin.py` | `SessionLocal` → repositories → commit | `_run_admin` async context | ✓ WIRED | CLI builds repositories, never raw SQL; commit in helper. |
| `seed.py` | `criterion_vocabulary` | `load_vocabulary_file` + `_load_vocabulary` | ✓ WIRED | Inserts only into `CriterionVocabularyModel`; grid criteria come from `category-1.json`. |
| `SqlAlchemyCriterionRepository.list_for_category` | `criterion_vocabulary` / `category_criteria` flags | defaults − exclusions ∪ includes | ✓ WIRED | Ancestors + descendants retained, so option nodes stay. |
| `0002` | `models.py` | `Base.metadata` via `migrations/env.py` | ✓ WIRED | Columns/types match; upgrade and downgrade both applied successfully. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `GET /api/v1/categories` | `list[Category]` | `SqlAlchemyCategoryRepository.list_all` | Yes — 158 rows from PostGIS | ✓ FLOWING |
| `GET /api/v1/categories/{slug}/criteria` | tree | `list_for_category` + `_build_tree` | Yes — 4 roots / 38 option nodes for `restaurant` | ✓ FLOWING |
| `GET /api/v1/filters` | `list[AccessibilityFilter]` | `list_active` | Yes — 52 rows | ✓ FLOWING |
| `GET /api/v1/other-information` | `list[OtherInformation]` | `list_all` | Yes — 15 rows | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Migration round-trip | `alembic downgrade 0001 && alembic upgrade head` | table and columns dropped then restored; `0002 (head)` | ✓ PASS |
| Seed idempotence | `python -m letmegetin.seed` twice | `created=182` then `created=0 skipped=182`; counts unchanged (182/158/61/19/0) | ✓ PASS |
| Real read path | direct repositories + `get_category_tree` on live DB | 158 categories, 52 filters, 15 OI, 4 roots, 38 options | ✓ PASS |
| CLI surface | `python -m letmegetin.admin --help` | lists all six command groups | ✓ PASS |
| Read-only CLI commands | `category list`, `criterion list --category restaurant`, `vocabulary list --unpromoted` | rows returned | ✓ PASS |

### Probe Execution

N/A — no phase-declared or conventional `scripts/*/tests/probe-*.sh` probes exist.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/unit/test_admin.py` | REF-02, REF-05 | 20+ | 0 | No | Behavioral | ✓ PASS |
| `tests/unit/test_api.py` | REF-01, REF-02, REF-03 | 8 | 0 | No | Value (`label == five-locale map`), Behavioral (option node) | ✓ PASS |
| `tests/unit/test_labels.py` | REF-05 | 5 parametrized | 0 | No | Value | ✓ PASS |
| `tests/integration/test_admin_cli.py` | REF-05 | 3 | 0 | No | Behavioral (real PostGIS) | ✓ PASS |
| `tests/integration/test_seed_vocabulary.py` | REF-04 | 2 | 0 | No | Value (counts from committed JSON) | ✓ PASS |

**Disabled tests on requirements:** 0. **Circular patterns detected:** 0. **Insufficient assertions:** 0.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REF-01 | 02-01 | API lists categories with multilingual labels (fr/en/es/de/it) | ✓ SATISFIED | 158 categories served from DB; five-locale JSONB map passes through unchanged (`test_endpoints_return_full_label_maps`). See observation below on seeded translations. |
| REF-02 | 02-01 | API exposes the criteria tree per category (groups → criteria → options) | ✓ SATISFIED | Real tree depth 4 with 38 option nodes; `test_criteria_tree_exposes_description_and_option_nodes`. |
| REF-03 | 02-01 | API lists accessibility filters and official labels | ✓ SATISFIED | 52 filters / 15 other-information from PostGIS; filter `position` preserved. |
| REF-04 | 02-01 | Seed loaded from reconstructed data (158 categories, 182 vocabulary rows, category-1 grid) | ✓ SATISFIED | DB counts 158/182/61; vocabulary never inserted into `criteria`; idempotent. |
| REF-05 | 02-01 | Minimal admin/CLI edits categories, criteria and options | ✓ SATISFIED | Six command groups; integration tests exercise every write path against PostGIS. |

**Observation (non-blocking):** seeded category labels currently carry only `it` (`criterion_vocabulary` carries `fr`+`it`). The API and label helpers support all five locales and the reads pass a complete map through; `02-CONTEXT.md` explicitly defers machine translation and states labels are set manually by the CLI, and the plan's must-have is "a label can hold all five locales". Treated as the documented phase boundary, not a gap; a translation pass is future work.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None (no `TBD`/`FIXME`/`XXX`, no placeholder/stub returns, no skipped requirement tests) | — | — |

Conditional `pytest.skip` calls in the two integration modules are the documented "no Docker → skip" guard, not disabled requirement tests — both files ran and passed here (6 integration tests).

### Human Verification Required

N/A — infrastructure/foundation phase (referential schema, seed, read API and an operator CLI) with no end-user-facing UI; all acceptance criteria verified programmatically. No behavior-unverified truths (link/unlink exclusion, idempotent seed and migration round-trip are all exercised by passing tests).

### Gaps Summary

No gaps. Every must-have truth, artifact, key link and data-flow trace passes against the real PostGIS database. Migration 0002 round-trips cleanly, `seed` is idempotent at 182 vocabulary / 158 categories / 61 grid criteria / 19 defaults / 0 materialized mapping rows, the flat vocabulary never pollutes `criteria`, and the Typer CLI performs all required edits end to end. CI on PR #5 is green (6/6 jobs).

---

_Verified: 2026-10-27T10:44:48Z_
_Verifier: the agent (gsd-verifier)_
