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

uv run python -m letmegetin.seed            # load the committed seed into the database
uv run uvicorn letmegetin.main:app --reload
# http://localhost:8000/docs  •  /health  •  /api/v1/categories
```

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
