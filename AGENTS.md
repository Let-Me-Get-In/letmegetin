# AGENTS.md — Jaccede v5

## Projet

Réécriture moderne du guide collaboratif de lieux accessibles (jaccede.com). Référentiel d'accessibilité normalisé + API publique FastAPI + frontend Next.js.

Le dossier `.planning/` (GSD) est la source de vérité : `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`.

## Stack

- **Backend** : Python 3.12+, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic, PostgreSQL 16 + PostGIS, `uv`.
- **Frontend** (à venir) : Next.js (App Router), TypeScript, Tailwind, MapLibre/OSM.
- **Qualité** : ruff, mypy, bandit, pytest.

## Commandes

```bash
docker compose up -d
uv sync
uv run python scripts/build_referential.py
uv run python -m jaccede.seed
uv run uvicorn jaccede.main:app --reload
uv run pytest
uv run ruff check . && uv run mypy
```

## Conventions

- `from __future__ import annotations` dans chaque module.
- Annotations de type obligatoires ; `str | None` (pas `Optional`).
- Longueur de ligne 100 (ruff).
- Pas de commentaire qui répète le code ; commenter le *pourquoi*.
- Modèles SQLAlchemy 2.0 typés (`Mapped[...]`, `mapped_column`).
- i18n : colonnes `JSONB` `{"fr": ..., "en": ...}`.
- Tests : pytest, un test par comportement ; pas d'appel réseau réel.
- Commits : Conventional Commits (`feat(api): ...`).

## Décisions clés

- FastAPI (pas Django) ; back-office minimal puis enrichi.
- PostGIS + JSONB i18n.
- Seed reconstitué (pas de dump historique) ; grille catégorie 1 comme base universelle, éditable.
- V1 sans gamification / messagerie / mobile.

## GSD

- Ne pas modifier `.planning/` à la main hors des workflows GSD.
- Prochaine étape : `/gsd-plan-phase 1` (ou `/gsd-discuss-phase 1`).
