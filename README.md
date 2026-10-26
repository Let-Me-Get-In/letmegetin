# LetMeGetIn

Réécriture moderne de Jaccede : un **référentiel d'accessibilité normalisé** exposé par une **API FastAPI** publique, consommable par des tiers et par notre frontend Next.js.

## Monorepo

- **Backend** (racine) : FastAPI + SQLAlchemy 2 async + PostgreSQL/PostGIS.
- **Frontend** : `web/` — Next.js (App Router), TypeScript, Tailwind, MapLibre (à venir).
- **E2E** : plus tard, dans un dépôt séparé.

## Démarrage

```bash
docker compose up -d                        # PostGIS sur localhost:55433
uv sync
git config core.hooksPath .githooks         # active le hook commit-msg (une fois par clone)
uv run python scripts/build_referential.py  # (re)génère data/referential/*.json
uv run python -m letmegetin.seed            # charge le seed en base
uv run uvicorn letmegetin.main:app --reload
# http://localhost:8000/docs  •  /health  •  /api/v1/categories
```

## Qualité

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run bandit -r src -c pyproject.toml
uv run pytest
```

## Conventions

- **Linear** : chaque branche/commit/PR commence par `LET-<n>` (team `LET`, projet `LetMeGetIn`). Voir `.planning/LINEAR.md`.
- Branche : `LET-<n>-<slug>` — Commit/PR : `LET-<n> <type>(<scope>): <description>`.
- Le hook `.githooks/commit-msg` force la convention (et rejette `feat(01-02)`).
- Détails complets : [AGENTS.md](AGENTS.md) et [CLAUDE.md](CLAUDE.md).

## GSD

Le projet est piloté par GSD (`.planning/`). Prochaine étape : `/gsd-plan-phase 1` (ou `/gsd-discuss-phase 1`).
