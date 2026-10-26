# Jaccede v5

Réécriture moderne du guide collaboratif des lieux accessibles aux personnes en situation de handicap : un **référentiel d'accessibilité normalisé** exposé par une **API FastAPI** publique, consommable par des tiers et par notre frontend Next.js.

## Démarrage

```bash
# 1. Base PostgreSQL + PostGIS
docker compose up -d

# 2. Dépendances Python
uv sync

# 3. Seed du référentiel (158 catégories, 182 critères, 52 filtres, grille catégorie 1)
uv run python scripts/build_referential.py   # (re)génère data/referential/*.json
uv run python -m jaccede.seed                # charge le seed en base

# 4. API
uv run uvicorn jaccede.main:app --reload
# http://localhost:8000/docs  •  /health  •  /api/v1/categories
```

## Structure

```
.planning/                 # GSD : PROJECT, REQUIREMENTS, ROADMAP, STATE
data/referential/          # seed généré (categories, criteria, filters, th, grille cat-1)
  raw/                     # sources historiques (CSV v4, doc API v3)
scripts/build_referential.py
src/jaccede/
  config.py                # pydantic-settings (JACCEDE_*)
  db.py                    # engine/session async
  models.py                # Category, Criterion, AccessibilityFilter, OtherInformation
  schemas.py               # Pydantic v2
  api.py                   # /api/v1/{categories,criteria,filters,other-information}
  seed.py                  # charge le seed
  main.py                  # app FastAPI + /health
tests/
```

## Qualité

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run bandit -r src -c pyproject.toml
uv run pytest
```

## Contexte de reconstitution

Le code de production historique n'existe plus (dumps S3 supprimés). Le référentiel est reconstruit depuis les dépôts encore disponibles (`jaccede-api-v4`, `jaccede-v3`) : voir `.planning/PROJECT.md`. La grille exacte par catégorie n'est pas récupérable à 100 % ; la base universelle (catégorie 1) est étendue et rendue éditable.

## GSD

Le projet est piloté par GSD. Prochaine étape : `/gsd-plan-phase 1` (ou `/gsd-discuss-phase 1`).
