---
phase: 02-referential-seed
plan: 01
subsystem: referential
tags: [referential, vocabulary, cli, typer, alembic, postgis]
requires:
  - phase-1 referential read schema (0001) and read API
provides:
  - criterion_vocabulary table (migration 0002)
  - criteria.is_default and category_criteria.excluded mapping flags
  - letmegetin-admin Typer CLI (categories, criteria, vocabulary, mapping, labels)
  - data-driven default mapping (defaults minus exclusions plus includes)
affects:
  - src/letmegetin/seed.py
  - src/letmegetin/api/v1/referential.py (read contract unchanged, resolution changed)
tech-stack:
  added: ["typer>=0.12.0"]
  patterns:
    - "domain ports + application use cases + SQLAlchemy adapters"
    - "JSONB label maps over fr/en/es/de/it"
key-files:
  created:
    - migrations/versions/0002_referential_curation.py
    - src/letmegetin/domain/referential/labels.py
    - src/letmegetin/admin.py
    - tests/unit/test_admin.py
    - tests/unit/test_labels.py
    - tests/integration/test_admin_cli.py
    - tests/integration/test_seed_vocabulary.py
  modified:
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/infrastructure/persistence/mappers.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/domain/referential/entities.py
    - src/letmegetin/domain/referential/repositories.py
    - src/letmegetin/core/exceptions.py
    - src/letmegetin/application/referential/admin.py
    - src/letmegetin/seed.py
    - tests/unit/test_seed.py
    - tests/unit/test_api.py
    - pyproject.toml
    - uv.lock
    - README.md
    - AGENTS.md
decisions:
  - "The default mapping is data: criteria.is_default plus category_criteria.excluded, resolved on read"
  - "Migration 0002 resets the Phase 1 materialized category_criteria rows so is_default is authoritative"
  - "Integration tests use a NullPool sessionmaker because each CLI/seed call runs its own asyncio.run loop"
metrics:
  duration: "~2h"
  tasks: 3
  commits: 3
  completed: 2026-10-27
actuals:
  tokens: 58000
  tasks: 3
  commits: 3
status: complete
---

# Phase 2 Plan 01: Referential Seed Summary

The 182 flat Jaccede labels now live in `criterion_vocabulary`, the category-to-criteria mapping is data (`is_default` / `excluded`), and a Typer CLI edits categories, criteria, options, mappings and five-locale labels against PostGIS.

## What was built

**Task 1 — vocabulary import end to end.** Alembic `0002` adds `criterion_vocabulary`, `criteria.is_default` and `category_criteria.excluded`, and backfills `is_default` on the category-1 grid of an already-seeded database. A `VocabularyEntry` entity, `VocabularyRepository` port, mapper, `SqlAlchemyVocabularyRepository`, `load_vocabulary_file` / `import_vocabulary` use cases and `letmegetin-admin vocabulary import` complete the vertical slice. `typer>=0.12.0` joined the dependencies with `uv.lock` moved in the same commit.

**Task 2 — the write surface.** `domain/referential/labels.py` parses, normalizes and merges `fr/en/es/de/it` maps. Ports gained `add`/`update` (category, criterion), `list_all`/`get_by_slug` (criterion) and `MappingRepository.set_state(include|exclude|clear)`. `SqlAlchemyCriterionRepository.list_for_category` now resolves *defaults minus exclusions plus includes*, then adds their ancestors and the descendants of the resolved criteria so option nodes stay in the tree. Use cases cover add/edit category, add/edit criterion, link/unlink, `promote_vocabulary` and three label setters; the CLI exposes `category`, `criterion`, `vocabulary`, `labels`, `link` and `unlink`.

**Task 3 — seed and reads.** `seed()` upserts `criteria.json` into `criterion_vocabulary`, marks only the second-level grid nodes `is_default`, no longer materializes `category_criteria` rows and reports created/skipped counts. New tests prove the five-locale label maps on the four read endpoints and a third-level option node in the tree. README documents every command group; AGENTS.md notes the CLI is the only write path until auth exists.

## Verification

| Check | Result |
|---|---|
| `alembic upgrade head` / `downgrade 0001` / `upgrade head` | clean both ways |
| `seed` twice | `vocabulary=182 categories=158 criteria=61 is_default=19 category_criteria=0`, unchanged on the second run |
| `vocabulary import` twice | `created=182` then `created=0 skipped=182` |
| `pytest` full suite | 84 passed, 97.49% line+branch (floor 85%) |
| ruff check / format / mypy / bandit | clean |
| `GET /categories`, `/categories/{slug}/criteria`, `/filters`, `/other-information` | 200 with JSONB maps (158 / 4 groups / 52 / 15) |

## Deviations from Plan

**1. [Rule 2 - Missing critical functionality] Migration 0002 resets the Phase 1 mapping rows**
- **Found during:** Task 3 verification
- **Issue:** Phase 1 materialized 3002 `category_criteria` rows. With them present, an `criterion edit --no-default` could not remove a criterion from a category because the leftover include row still kept it linked, defeating the "defaults minus exclusions" must-have.
- **Fix:** `op.execute("DELETE FROM category_criteria")` at the end of `0002.upgrade()`, after `is_default` is backfilled. It is a one-shot reset, a no-op on a fresh database, and runs before the CLI can write any include row.
- **Impact:** the downgrade cannot restore the deleted rows; the effective mapping is identical because the same criteria carry `is_default = true`.

**2. [Rule 1 - Bug] `test_api.test_category_criteria_tree` updated for the new read**
- **Found during:** Task 2
- **Issue:** the fake session queued a bare id where the repository now reads `CategoryCriterionModel.excluded`.
- **Fix:** the fake returns the link model, in the new query order (criteria, then links).

**3. [Rule 3 - Blocking] Integration tests use a `NullPool` sessionmaker**
- **Found during:** Task 1
- **Issue:** `CliRunner` and `seed()` each call `asyncio.run`, and a pooled asyncpg connection cannot be reused from a second event loop.
- **Fix:** the integration modules build a `NullPool` engine/sessionmaker and monkeypatch `admin.SessionLocal` / `seed.SessionLocal`. Production pooling is untouched.

**4. Coverage gate scope.** Task 2's literal `--cov-fail-under=85` over two test files cannot pass (whole-package coverage measured from a subset). The gate is evaluated on the full suite, which is the plan's own verification item 4.

## Known Stubs

None. `vocabulary promote` derives the criterion slug from the French label via `slugify`, which is the documented behaviour, not a placeholder.

## Threat Flags

None beyond the plan's register. The CLI adds no network surface, and errors echo the domain message only (the integration test asserts no SQL text leaks).

## Self-Check: PASSED

- Created files exist: `0002_referential_curation.py`, `labels.py`, `admin.py`, `test_admin.py`, `test_labels.py`, `test_admin_cli.py`, `test_seed_vocabulary.py`, this SUMMARY.
- Commits exist: `ca2cdd2`, `9239676`, `74b954f` all ancestors of `HEAD`.
