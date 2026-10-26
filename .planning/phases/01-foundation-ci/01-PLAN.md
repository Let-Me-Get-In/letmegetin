---
phase: 01-foundation-ci
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - alembic.ini
  - migrations/env.py
  - migrations/script.py.mako
  - migrations/versions/0001_initial.py
  - src/letmegetin/seed.py
  - tests/test_api.py
  - tests/test_seed.py
  - tests/test_utils.py
  - .github/workflows/ci.yml
  - .pre-commit-config.yaml
  - .githooks/pre-commit
  - pyproject.toml
  - uv.lock
  - README.md
  - AGENTS.md
autonomous: true
requirements:
  - OPS-01
  - OPS-02
  - OPS-03
user_setup: []
ticket: LET-6

estimate:
  tokens: 45000
  raw_tokens: 30000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "After `docker compose up -d --wait db` and `uv run alembic upgrade head`, the five referential tables exist in PostGIS and `GET /health` still returns 200 (OPS-01, OPS-03)."
    - "`uv run python -m letmegetin.seed` no longer creates schema; it loads the committed JSON into a schema already managed by Alembic (OPS-03)."
    - "`.github/workflows/ci.yml` defines lint, typecheck, sast and test jobs on pull_request and push to main; the test job enforces an 80% branch coverage floor (OPS-02)."
    - "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run bandit -r src -c pyproject.toml` and `uv run pytest --cov=letmegetin --cov-branch --cov-fail-under=80` all pass locally (OPS-02)."
    - "`.pre-commit-config.yaml` wires ruff, bandit, gitleaks and file-hygiene hooks; `.githooks/commit-msg` remains the commit-convention source of truth (OPS-02)."
  artifacts:
    - path: "alembic.ini"
      provides: "Alembic entry point (script_location = migrations)"
    - path: "migrations/env.py"
      provides: "Async Alembic environment reading settings.database_url and Base.metadata"
    - path: "migrations/versions/0001_initial.py"
      provides: "Initial schema for categories, criteria, category_criteria, accessibility_filters, other_information"
    - path: ".github/workflows/ci.yml"
      provides: "Required lint/typecheck/sast/test jobs, Python 3.12 + uv --frozen, 80% coverage floor"
    - path: ".pre-commit-config.yaml"
      provides: "Local quality gates matching CI"
    - path: "tests/test_api.py"
      provides: "Route-level tests via dependency override (no database)"
    - path: "tests/test_seed.py"
      provides: "Seed loader tests with a fake async session (no database)"
    - path: "tests/test_utils.py"
      provides: "slugify tests"
  key_links:
    - "migrations/env.py imports `settings.database_url` and `Base.metadata`; it must not hard-code credentials."
    - "The 0001 migration mirrors `src/letmegetin/models.py` exactly (columns, indexes, FKs, JSONB, unique constraints)."
    - "The CI `test` job must run the same pytest command that passes locally, including `--cov-fail-under=80`."
    - "`src/letmegetin/seed.py` must not reference `engine` or `Base.metadata.create_all` after this plan."
---

<objective>
Complete Phase 1 (Foundation & CI, ticket LET-6) by adding Alembic-managed schema migrations, removing schema creation from the seed script, and gating every pull request with lint, type checking, security scanning and coverage-enforced tests.

Purpose: make the backend reproducible. Today `seed.py` creates tables as a side effect and no migration history exists, so schema changes are invisible and CI cannot protect them. After this plan the database schema is versioned, seed data is separate from schema creation, and CI plus pre-commit enforce the project's quality bar.

Output: `alembic.ini` + `migrations/` with an async `env.py` and `0001_initial`; a seed script that assumes `alembic upgrade head`; unit tests that lift coverage over 80% without a database; `.github/workflows/ci.yml`; `.pre-commit-config.yaml`; updated quick-start docs.
</objective>

<execution_context>
@/Users/seb/.config/opencode/gsd-core/workflows/execute-plan.md
@/Users/seb/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation-ci/01-CONTEXT.md
@AGENTS.md
@README.md
@pyproject.toml
@docker-compose.yml
@src/letmegetin/config.py
@src/letmegetin/db.py
@src/letmegetin/models.py
@src/letmegetin/seed.py
@src/letmegetin/api.py
@src/letmegetin/utils.py
@tests/test_health.py
@tests/test_build_referential.py
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Wire Alembic async migrations end-to-end and create 0001_initial</name>
  <files>alembic.ini, migrations/env.py, migrations/script.py.mako, migrations/versions/0001_initial.py</files>
  <precondition>`docker compose up -d --wait db` has started the PostGIS container (`letmegetin-db`, host port 55433) and its healthcheck passes.</precondition>
  <action>
Create the Alembic scaffold at the repository root, wired to the existing async settings and models, and prove it end-to-end against the live PostGIS container (OPS-03).

`alembic.ini`: set `script_location = migrations`, `prepend_sys_path = .`, leave `sqlalchemy.url` empty (the env module supplies it from settings), and keep the standard logging sections. Do not commit a database URL with credentials here.

`migrations/env.py`: an async Alembic environment. Import `Base` and every model module from `letmegetin.models`, import `settings` from `letmegetin.config`, set `target_metadata = Base.metadata`, and create the engine with `create_async_engine(settings.database_url)` inside `run_migrations_online()`. Support both offline mode (`context.configure(url=settings.database_url, target_metadata=..., literal_binds=True)`) and online mode (open a connection, `await connection.run_sync(do_run_migrations)`, dispose the engine). Use only `settings.database_url`; never hard-code credentials.

`migrations/script.py.mako`: the standard Alembic revision template (`upgrade()` / `downgrade()` with `${up_revision}`, `${down_revision}`, `${message}`).

`migrations/versions/0001_initial.py`: revision `0001`, `down_revision = None`, and create exactly the tables in `src/letmegetin/models.py`. Mirror the models column for column, including: `categories` (id PK, slug varchar(120) unique + index, name varchar(120) non-null, label JSONB non-null, parent_id FK categories.id nullable + index, created/updated timestamp with `server_default=sa.text("now()")`); `criteria` (id, slug varchar(200) unique + index, parent_id FK criteria.id nullable + index, type varchar(16), position integer, need_children boolean, label JSONB, description JSONB, created/updated); `category_criteria` (category_id FK categories.id `ondelete="CASCADE"` and criterion_id FK criteria.id `ondelete="CASCADE"`, both primary key); `accessibility_filters` (id, slug varchar(200) unique + index, label JSONB, criterion_id FK criteria.id nullable, position integer, active boolean, created/updated); `other_information` (id, slug varchar(120) unique + index, name varchar(120) non-null, label JSONB, link varchar(500) nullable, parent_id FK other_information.id nullable, created/updated, unique constraint `other_information_name_uc` on name). Use `sqlalchemy.dialects.postgresql.JSONB` for the JSON columns. Create indexes with the exact names Alembic autogenerate derives, using `unique=True` where the model declares `unique=True, index=True`: `op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)`, `ix_criteria_slug`, `ix_accessibility_filters_slug`, `ix_other_information_slug`; plus `ix_categories_parent_id` and `ix_criteria_parent_id`. `accessibility_filters.criterion_id` has **no** index in the model. Declare `other_information_name_uc` as a unique constraint on `other_information.name`. `downgrade()` drops the tables in reverse dependency order (other_information, accessibility_filters, category_criteria, criteria, categories).

Do not add a geometry column or PostGIS extension creation: Phase 1 models have none, and the PostGIS image enables the extension. Do not edit `models.py`.
  </action>
  <verify>
    <automated>docker compose up -d --wait db && uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head && test "$(docker exec letmegetin-db psql -U letmegetin -d letmegetin -tAc "select count(*) from information_schema.tables where table_name in ('categories','criteria','category_criteria','accessibility_filters','other_information')")" = "5"</automated>
  </verify>
  <done>`uv run alembic upgrade head` creates all five tables; `uv run alembic downgrade base` drops them; re-upgrading restores them; `uv run alembic current` reports `0001`. No credentials are committed in `alembic.ini`.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Decouple seed from schema creation, document the start path, and add unit tests to clear 80% coverage</name>
  <files>src/letmegetin/seed.py, tests/test_api.py, tests/test_seed.py, tests/test_utils.py, pyproject.toml, README.md, AGENTS.md</files>
  <precondition>`uv run alembic upgrade head` from Task 1 has been applied to the running PostGIS database.</precondition>
  <behavior>
    - `tests/test_utils.py`: `slugify("ENTRÉE") == "entree"`, `slugify("a b/c") == "a-b-c"`, `slugify("!!!") == "item"`, and accents/whitespace collapse stably.
    - `tests/test_api.py`: overriding `get_session` with a fake async session, `GET /api/v1/categories` returns 200 and the category slug; `GET /api/v1/categories/{slug}/criteria` returns 200 with a nested root/child tree, and 404 when the category is missing; `GET /api/v1/filters` and `GET /api/v1/other-information` return 200.
    - `tests/test_seed.py`: `_criterion_type` maps `user_value` with "(cm)" to `integer`, other `user_value` to `string`, payloads with options to `option`, and empty payloads to `boolean`; `seed()` against a fake `SessionLocal` and a temporary `data_dir` inserts categories, filters, other information and the category-1 tree without creating any schema.
  </behavior>
  <action>
Remove schema creation from `src/letmegetin/seed.py`: delete the `async with engine.begin()` block that calls `Base.metadata.create_all`, and remove the now-unused `engine` and `Base` imports. Update the module docstring to state that the schema must exist first (`uv run alembic upgrade head`) and that the script is idempotent. Do not add a `--create-schema` flag; the migration is the only schema path.

Update the quick start so the documented path is runnable (OPS-01): in `README.md` and the Commands section of `AGENTS.md`, insert `uv run alembic upgrade head` between `uv sync` and `uv run python -m letmegetin.seed`. Keep the existing `docker compose up -d` and `uv run uvicorn` steps; add one sentence that `docker compose up -d --wait db` + `uv run alembic upgrade head` + `uv run uvicorn letmegetin.main:app` is the one-command-equivalent smoke path and that `GET /health` returns `{"status": "ok"}`. Do not introduce a new shell script.

Add `pytest-cov` to the `dev` dependency group in `pyproject.toml` and refresh `uv.lock` with `uv lock` (or `uv add --dev pytest-cov`). Add `[tool.mypy] files = ["src", "scripts"]` so the documented bare `uv run mypy` command has targets.

Write the three test modules described in `<behavior>`. For the API tests, override `letmegetin.api.get_session` via `app.dependency_overrides` and clear it in fixture teardown; do not connect to PostgreSQL. For the seed test, monkeypatch `letmegetin.seed.SessionLocal` with a factory returning an async context manager around a fake session that implements `scalar`, `scalars`, `add`, `flush` and `commit`, and point `settings.data_dir` at a `tmp_path` tree containing small `categories.json`, `filters.json`, `th.json` and `category_grids/category-1.json` fixtures. Give inserted objects an `id` on `add` so the association loop runs. Use `@pytest.mark.parametrize` and `ids=` for multi-case inputs per AGENTS.md.
  </action>
  <verify>
    <automated>uv run pytest tests/test_api.py tests/test_seed.py tests/test_utils.py -q --cov=letmegetin --cov-branch --cov-fail-under=80</automated>
  </verify>
  <done>`seed.py` contains no reference to `engine` or `Base.metadata.create_all`; README and AGENTS document `alembic upgrade head` before seeding; the three new test modules pass and total branch coverage over `letmegetin` is at least 80% with no database connection.</done>
</task>

<task type="auto">
  <name>Task 3: Add CI workflow and pre-commit config matching the local quality commands</name>
  <files>.github/workflows/ci.yml, .pre-commit-config.yaml, pyproject.toml, AGENTS.md</files>
  <action>
Create `.github/workflows/ci.yml` (OPS-02). Triggers: `pull_request` and `push` to `main`. Set `permissions: contents: read` and a `concurrency` group keyed on the workflow and ref with `cancel-in-progress: true`. Do not use `pull_request_target` and do not reference any secrets. Every job runs on `ubuntu-latest`, sets up Python 3.12 via `astral-sh/setup-uv` (enable caching), then runs `uv sync --frozen` (the default group already includes `dev`).

Jobs (names exactly `lint`, `typecheck`, `sast`, `test`):
- `lint`: `uv run ruff check .` then `uv run ruff format --check .`
- `typecheck`: `uv run mypy` (relies on the new `files` setting in `pyproject.toml`)
- `sast`: `uv run bandit -r src -c pyproject.toml`
- `test`: `uv run pytest --cov=letmegetin --cov-branch --cov-report=term-missing --cov-fail-under=80`

Create `.pre-commit-config.yaml` with: `astral-sh/ruff-pre-commit` hooks `ruff` (args `--fix`) and `ruff-format`; `PyCQA/bandit` hook `bandit` (args `-c pyproject.toml`, so it scans only the staged Python files); `gitleaks/gitleaks` hook `gitleaks`; and `pre-commit/pre-commit-hooks` hooks `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`, `check-merge-conflict`. Pin each `rev` and keep the versions current. Do not add a `commit-msg` stage hook: `.githooks/commit-msg` stays the single source of truth. Because `core.hooksPath` points at `.githooks`, `pre-commit install` refuses to run ("Cowardly refusing to install hooks with core.hooksPath set"), so instead add a `.githooks/pre-commit` wrapper that executes `uv run pre-commit run --hook-stage pre-commit`, make it executable, and document in `AGENTS.md` that contributors only need `git config core.hooksPath .githooks` (no `pre-commit install`).

Add `pre-commit` to the `dev` dependency group in `pyproject.toml` and refresh `uv.lock`. Do not modify `.githooks/commit-msg`.
  </action>
  <verify>
    <automated>uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run bandit -r src -c pyproject.toml && uv run pytest -q --cov=letmegetin --cov-branch --cov-fail-under=80 && uv run pre-commit run --all-files && ! grep -q pull_request_target .github/workflows/ci.yml && grep -q "permissions: contents: read" .github/workflows/ci.yml && ! grep -q "secrets\." .github/workflows/ci.yml && for j in lint typecheck sast test; do grep -q "^  $j:" .github/workflows/ci.yml; done</automated>
  </verify>
  <done>`.github/workflows/ci.yml` declares the four required jobs on PR and main with Python 3.12 + `uv sync --frozen` and an 80% coverage floor; `.pre-commit-config.yaml` runs ruff, bandit, gitleaks and hygiene hooks; the full local quality suite passes; `.githooks/commit-msg` is unchanged.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GitHub PR (including forks) → CI runner | Untrusted code executes in Actions; workflow must not expose secrets or write privileges |
| Developer machine → git history | Pre-commit and gitleaks scan staged content before it is committed |
| Application → PostgreSQL | Migration DDL and seed writes cross into the database; credentials come from environment |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-01-01 | Elevation of privilege | `.github/workflows/ci.yml` | high | mitigate | Use `pull_request` (never `pull_request_target`), set `permissions: contents: read`, reference no secrets, so untrusted PR code cannot act with write scope. |
| T-01-02 | Information disclosure | `alembic.ini`, `migrations/env.py` | medium | mitigate | `sqlalchemy.url` is empty in `alembic.ini`; `env.py` reads only `settings.database_url` from environment; `.env` remains git-ignored. |
| T-01-03 | Tampering | Pre-commit hooks | medium | mitigate | gitleaks + bandit run before commit; behavioural change to `.githooks/commit-msg` is explicitly out of scope, so commit-convention enforcement is not weakened. |
| T-01-04 | Repudiation | Migration history | low | accept | `0001_initial` is the auditable baseline; later changes are new revisions. No destructive data exists yet in dev. |
| T-01-SC | Tampering | uv/dev dependency installs (`pytest-cov`, `pre-commit`) | high | mitigate | Only official, widely used packages; versions pinned in the committed `uv.lock`; CI runs `uv sync --frozen`. |
</threat_model>

<verification>
Run the full local gate after all three tasks:

- `docker compose up -d --wait db`
- `uv run alembic upgrade head` (tables exist) and `uv run alembic downgrade base` / `upgrade head` round-trip
- `uv run python -m letmegetin.seed` (loads data, does not create schema)
- `uv run ruff check . && uv run ruff format --check .`
- `uv run mypy`
- `uv run bandit -r src -c pyproject.toml`
- `uv run pytest --cov=letmegetin --cov-branch --cov-fail-under=80`
- `uv run pre-commit run --all-files`
</verification>

<success_criteria>
- `uv run alembic upgrade head` creates the five referential tables and `GET /health` returns 200 on the running API (OPS-01, OPS-03).
- `seed.py` no longer creates schema and runs against an Alembic-managed database (OPS-03).
- CI defines required `lint`, `typecheck`, `sast`, `test` jobs on PR and main, Python 3.12, `uv sync --frozen`, 80% branch coverage floor (OPS-02).
- The same commands pass locally: ruff check + format check, mypy, bandit, pytest with coverage (OPS-02).
- `.pre-commit-config.yaml` covers ruff, bandit, gitleaks and hygiene; `.githooks/commit-msg` remains the commit-convention source of truth (OPS-02).
</success_criteria>

<output>
Create `.planning/phases/01-foundation-ci/01-01-SUMMARY.md` when done.
</output>
