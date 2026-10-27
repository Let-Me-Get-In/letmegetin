# LetMeGetIn

A modern rewrite of Jaccede: a **normalized accessibility referential** exposed through a **public FastAPI API**, consumable by third parties and by our own Next.js frontend.

## Monorepo

- **Backend** (repo root): FastAPI + SQLAlchemy 2 async + PostgreSQL/PostGIS.
- **Frontend**: `web/` — Next.js (App Router), TypeScript, Tailwind, MapLibre (coming).
- **E2E**: later, in a separate repository.

## Quick start

```bash
docker compose up -d                        # PostGIS on localhost:55433
uv sync
git config core.hooksPath .githooks         # enable the commit-msg hook (once per clone)

uv run alembic upgrade head                 # versioned schema
uv run python -m letmegetin.seed            # load the committed seed into the database
uv run uvicorn letmegetin.main:app --reload
# http://localhost:8000/docs  •  /health  •  /api/v1/categories
```

The one-command-equivalent smoke path is
`docker compose up -d --wait db && uv run alembic upgrade head && uv run uvicorn letmegetin.main:app`:
`GET /health` returns `{"status": "ok"}`.

## Referential data

The normalized referential (158 categories, 182 criteria, 52 filters, 15 official
labels and the full category-1 grid) lives in `data/referential/*.json` and is
committed. It was reconstructed from the historical Jaccede sources.

The original raw sources are **private** and are **not** committed. They are only
needed to regenerate the JSON:

```bash
# with the private raw sources placed in data/referential/raw/
uv run python scripts/build_referential.py
```

## Admin CLI

`letmegetin-admin` (or `uv run python -m letmegetin.admin`) is the only write path
to the referential until authentication exists. It talks to the database with the
same async session as the API; the credentials in `LETMEGETIN_DATABASE_URL` are
the only gate.

```bash
uv run python -m letmegetin.admin --help

# Categories
uv run python -m letmegetin.admin category list
uv run python -m letmegetin.admin category add garden --name Garden --label fr=Jardin
uv run python -m letmegetin.admin category edit garden --label en=Garden

# Criteria and options (an option is a criterion with --type option and --parent)
uv run python -m letmegetin.admin criterion list --category restaurant
uv run python -m letmegetin.admin criterion add entree-automatique --type boolean \
  --parent entree --label fr=Automatique --default
uv run python -m letmegetin.admin criterion edit entree-automatique --no-default

# Category-to-criteria mapping
uv run python -m letmegetin.admin link restaurant entree-automatique
uv run python -m letmegetin.admin unlink restaurant entree-automatique

# Flat vocabulary (library of unassigned labels) and promotion into a criterion
uv run python -m letmegetin.admin vocabulary import
uv run python -m letmegetin.admin vocabulary list --query rampe --unpromoted
uv run python -m letmegetin.admin vocabulary promote rampe-amovible --type option \
  --parent entree-acces --category restaurant

# Multilingual labels
uv run python -m letmegetin.admin labels set criterion entree-automatique \
  --label en=Automatic --label es=Automática
```

Labels are JSONB maps over **fr, en, es, de, it**, set by hand: no machine
translation ships in this phase, and the API always returns the full map so the
client picks the locale.

The default mapping is data, not code: `criteria.is_default` marks the base set
and `category_criteria.excluded` records a per-category opt-out, so re-running
`uv run python -m letmegetin.seed` never undoes an operator decision.

## Quality

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run bandit -r src -c pyproject.toml
uv run pytest
```

## Conventions

- **Linear**: every branch/commit/PR starts with the ticket id (`LET-<n>`; team `LET`, project `LetMeGetIn`). See `.planning/LINEAR.md`.
- Branch: `LET-<n>-<slug>` — Commit/PR: `LET-<n> <type>(<scope>): <description>`.
- The `.githooks/commit-msg` hook enforces the convention (and rejects `feat(01-02)`).
- Full details: [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md).

## GSD

The project is driven by GSD (`.planning/`). Next step: `/gsd-plan-phase 1` (or `/gsd-discuss-phase 1`).
