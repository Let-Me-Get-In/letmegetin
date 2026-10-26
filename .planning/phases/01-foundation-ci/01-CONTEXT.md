# Phase 1: Foundation & CI - Context

**Gathered:** 2026-10-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Make LetMeGetIn a robust, reproducible foundation: the backend runs against
PostgreSQL/PostGIS, schema changes are versioned with Alembic, and every pull
request is gated by CI (lint, types, security, tests + coverage).

Out of scope: the referential API surface (Phase 2), places/search (Phase 3),
auth/contribution (Phase 5), the Next.js frontend (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Configuration & runtime
- Settings via `pydantic-settings`, env prefix `LETMEGETIN_` (`src/letmegetin/config.py`).
- Dev database: `postgresql+asyncpg://letmegetin:letmegetin@localhost:55433/letmegetin`
  (PostGIS container `letmegetin-db`, host port 55433).
- `docker compose up -d` provides PostGIS; the API runs with `uv run uvicorn`.

### Migrations (OPS-03)
- Use **Alembic** (async env, `render_as_batch` not needed on Postgres).
- Add `alembic.ini` + `migrations/` with an async `env.py` reading
  `settings.database_url` and `Base.metadata`.
- Create `0001_initial` for the current referential tables
  (`categories`, `criteria`, `category_criteria`, `accessibility_filters`,
  `other_information`).
- `src/letmegetin/seed.py` must stop calling `Base.metadata.create_all`; it should
  assume `alembic upgrade head` has run (keep `create_all` only behind an explicit
  `--create-schema` dev flag if needed).

### CI (OPS-02)
- GitHub Actions `.github/workflows/ci.yml` on `pull_request` and `push` to `main`.
- Jobs (all required): `lint` (ruff check + format --check), `typecheck` (mypy),
  `sast` (bandit), `test` (pytest + coverage). Python 3.12, `uv` with cache.
- Coverage: `pytest-cov` with `--cov-branch`, floor **80%** for now (raise later).
- No DB service required for Phase 1 tests: they are unit-level (seed parser +
  `/health`). A PostGIS integration job is deferred to Phase 3.

### Pre-commit & local hooks
- `.pre-commit-config.yaml`: ruff (lint+format), bandit, gitleaks, trailing
  whitespace / EOF / YAML checks.
- Keep the existing `.githooks/commit-msg` (Linear `LET-<n>` prefix) as the single
  source of truth for commit conventions; document `git config core.hooksPath .githooks`.

### Determinism / hygiene
- Pin `requires-python = ">=3.12"`; CI uses the latest 3.12.
- `uv.lock` is committed and `uv sync --frozen` is used in CI.

### Delivery / git workflow (milestone stack)
- The milestone is delivered as **one linear `gh stack`** (a single person works on it):
  `main ← LET-5 ← LET-6 ← … ← LET-12`. One phase = one stack layer = one PR, based on the layer below.
- PRs are merged **bottom-up**; merging is a human decision (never automated).
- `gh stack submit --auto --open` pushes and refreshes the stack; `gh stack sync` keeps it rebased.

### Agent's Discretion
- Exact Alembic file layout, workflow job naming, bandit skip list, and pre-commit
  hook versions.

</decisions>

<canonical_refs>
## Canonical References

### Project & conventions
- `AGENTS.md` — stack, commands, Linear/GSD conventions, commit rules.
- `CLAUDE.md` — non-negotiable GSD/commit rules.
- `README.md` — quick start, quality commands.
- `.planning/REQUIREMENTS.md` §Foundation & Ops — OPS-01/02/03.
- `.planning/ROADMAP.md` §Phase 1 — goal and success criteria.
- `.planning/LINEAR.md` — ticket LET-6.

### Code
- `pyproject.toml` — dependencies, ruff/mypy/bandit/pytest config.
- `docker-compose.yml` — PostGIS service.
- `src/letmegetin/config.py`, `db.py`, `models.py`, `main.py`.
- `src/letmegetin/seed.py` — currently calls `Base.metadata.create_all`.
- `tests/test_health.py`, `tests/test_build_referential.py`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/letmegetin/db.py` exposes `engine` and `SessionLocal` — reuse in Alembic `env.py`.
- `src/letmegetin/models.py` has `Base` and the referential tables — target for the initial migration.
- `tests/` already has 6 passing tests (parser + health) — the CI `test` job starts from here.

### Established Patterns
- `pydantic-settings` with `LETMEGETIN_` prefix.
- SQLAlchemy 2.0 typed models; JSONB labels.
- Conventional Commits with the `LET-<n>` ticket prefix (enforced by the hook).

### Integration Points
- CI reads `pyproject.toml` + `uv.lock`.
- Alembic reads `settings.database_url` and `Base.metadata`.

</code_context>

<deferred>
## Deferred Ideas

- PostGIS integration test job (needs a service container) — Phase 3.
- CD / deployment workflow — Phase 7.
- Coverage badge / Codecov — later.
- Dockerfile for the API — only when deployment is addressed.

</deferred>

---

*Phase: 01-foundation-ci*
*Context gathered: 2026-10-26*
