---
status: complete
phase: 02-referential-seed
source: 02-01-SUMMARY.md
started: 2026-10-27T11:30:00Z
updated: 2026-10-27T10:42:44.784Z
---

## Current Test

[testing complete]

## Tests

### 1. Vocabulary import end-to-end
expected: `vocabulary import` loads 182 labels; second run creates 0; no label pollutes the criteria tree.
result: pass
source: automated
evidence: "created=182 then created=0 skipped=182; criteria stays at 61 (category-1 grid only)"

### 2. Admin write surface
expected: `category add/edit`, `criterion add --type option --parent`, `link`/`unlink`, `labels set` (fr/en/es/de/it) and `vocabulary promote` run against PostGIS.
result: pass
source: automated
evidence: "Typer CLI commands tested; use cases covered by fake-repo unit tests; integration tests against real PostGIS"

### 3. Seed loads the vocabulary, keeps the tree clean
expected: `python -m letmegetin.seed` loads 182 vocabulary rows, 158 categories, 19 `is_default`, 0 materialized `category_criteria`; a second run changes nothing.
result: pass
source: automated
evidence: "seed twice: vocabulary=182 categories=158 criteria=61 is_default=19 category_criteria=0 (unchanged)"

### 4. Reads still serve multilingual maps
expected: `/categories` (158), `/categories/{slug}/criteria` (4 groups + option nodes), `/filters` (52), `/other-information` (15), labels over fr/en/es/de/it.
result: pass
source: automated
evidence: "200 + JSONB maps; a third-level option node is asserted in the tree"

### 5. Migration 0002 round-trip
expected: `alembic upgrade head` → `downgrade 0001` → `upgrade head` is clean; `0002` adds the table + columns + index.
result: pass
source: automated
evidence: "upgrade/downgrade/upgrade clean; `alembic current` = 0002 (head)"

### 6. CI green
expected: on PR #5, lint, typecheck, sast, secret-scan, unit and test (PostGIS + 85% floor) all pass.
result: pass
source: automated
evidence: "GitHub Actions run 40487421394: 6/6 jobs pass"

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
