# LetMeGetIn

## What This Is

LetMeGetIn est la réécriture moderne de **Jaccede** (guide collaboratif des lieux accessibles aux personnes en situation de handicap, 2002→2024). Il expose un **référentiel d'accessibilité normalisé** (catégories de lieux, critères hiérarchiques et typés, labels officiels) via une **API publique FastAPI** consommable par des tiers, et un **frontend Next.js** qui permet de rechercher des lieux, consulter leur fiche d'accessibilité et contribuer.

## Core Value

Permettre à quiconque de savoir, en quelques secondes, si un lieu est réellement accessible — grâce à une fiche d'accessibilité structurée et fiable, consommable par n'importe quel site ou application.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Référentiel : catégories, critères hiérarchiques typés, filtres, labels officiels, exposés par l'API
- [ ] Seed reconstitué depuis les archives de l'ancien Jaccede (158 catégories, 182 critères, grille complète d'une catégorie)
- [ ] Recherche de lieux géo + texte + filtres d'accessibilité
- [ ] Fiche lieu avec arbre d'accessibilité et avis
- [ ] Auth (JWT) + contribution (compléter une fiche, déposer un avis)
- [ ] Frontend Next.js : recherche (carte + liste), fiche, contribution, compte
- [ ] API publique : clés API, OpenAPI, documentation

### Out of Scope

- Gamification (challenges, équipes, points, trésor) — v2
- Messagerie / chat temps réel — v2
- Applications mobiles natives — plus tard (API-first)
- Import des référentiels partenaires (Macif, La Poste, LocalEyes, HandiPlage) — v2
- Modération avancée / back-office complet — admin minimal en v1

## Context

### Reconstruction (sources épuisées)

Le code de production Jaccede n'est plus accessible (buckets S3 supprimés, RDS mort, Wayback indisponible). La reconstitution s'appuie sur les dépôts privés encore présents :

| Source | Donnée |
|---|---|
| `jaccede-api-v4` (Flask, 2024) | Modèle `Criterion` (hiérarchique, 7 types), `Category`, `AccessibilityValue`, `OtherInformation`, importeurs partenaires |
| `commands/translations/it/*.csv` | 233 libellés critères/options, 158 catégories, 52 filtres, 16 labels TH |
| `jaccede-v3/docs/api/source/places_api.rst` | Grille **complète** de la catégorie 1 (4 groupes, 19 critères, options, types) |
| `apidocs/docs/categories.html` | 118 catégories avec libellés FR |
| `jaccede-dev-tools` + `jaccede-doc` | Confirment le dump S3 (supprimé) ; aucune donnée exploitable |

La grille fine par catégorie n'est pas récupérable à 100 % : on part de la grille catégorie 1 comme base universelle, on l'étend avec le vocabulaire et les mappings partenaires, et on rend l'ensemble **éditable en admin**.

### Monorepo

- **Backend** : racine du dépôt (`src/letmegetin`, `tests/`, `data/`).
- **Frontend** : `web/` (Next.js, à venir).
- **E2E** : plus tard, dans un **dépôt séparé** (comme interview-challenger).

### Suivi

Linear : workspace `exstrat`, team **LMG**, project **LetMeGetIn**. Chaque branche/commit/PR commence par `LMG-<n>`. Mapping dans `.planning/LINEAR.md`.

## Constraints

- **Backend** : FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic.
- **Frontend** : Next.js (App Router) + TypeScript + Tailwind + MapLibre/OSM.
- **BDD** : PostgreSQL + PostGIS (recherche géo), port dev **55433**.
- **Qualité** : ruff, mypy, bandit, pytest + coverage, pre-commit.
- **Pas de dépendance dure à Google Places** : seed local, enrichissement optionnel.
- **Données historiques** : ne pas prétendre à une copie 1:1 ; conserver idées, vocabulaire et structure.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI (pas Django) | Async, OpenAPI auto, écosystème de l'auteur | — Pending |
| Next.js (pas SvelteKit) | SEO/SSR, écosystème a11y, cartes | — Pending |
| PostGIS + JSONB i18n | Recherche géo native ; i18n simple | — Pending |
| Seed reconstitué (pas de dump) | Seule donnée disponible ; éditable | — Pending |
| Monorepo back + front | Simplicité pour l'instant ; e2e séparé plus tard | — Pending |
| Linear (team LMG) en tête de branche/commit/PR | Traçabilité ticket ↔ code | — Pending |
| V1 sans gamification/messagerie/mobile | Recentrage sur le cœur | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-26 after rename to LetMeGetIn*
