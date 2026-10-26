# Jaccede v5

## What This Is

Jaccede v5 est la réécriture moderne du guide collaboratif des lieux accessibles aux personnes en situation de handicap (jaccede.com, 2002→2024). Le produit expose un **référentiel d'accessibilité normalisé** (catégories de lieux, critères hiérarchiques et typés, labels officiels) via une **API publique FastAPI** consommable par des tiers, et un **frontend Next.js** qui permet de rechercher des lieux, consulter leur fiche d'accessibilité et contribuer.

## Core Value

Permettre à quiconque de savoir, en quelques secondes, si un lieu est réellement accessible — grâce à une fiche d'accessibilité structurée et fiable, consommable par n'importe quel site ou application.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Référentiel : catégories, critères hiérarchiques typés, filtres, labels officiels, exposés par l'API
- [ ] Seed reconstitué depuis les archives de l'ancien produit (158 catégories, 233 libellés, grille complète d'une catégorie)
- [ ] Recherche de lieux géo + texte + filtres d'accessibilité
- [ ] Fiche lieu avec arbre d'accessibilité et avis
- [ ] Auth (JWT) + contribution (compléter une fiche, déposer un avis)
- [ ] Frontend Next.js : recherche (carte + liste), fiche, contribution, compte
- [ ] API publique : clés API, OpenAPI, documentation

### Out of Scope

- Gamification (challenges, équipes, points, trésor) — v2, non essentiel au cœur référentiel
- Messagerie / chat temps réel — v2
- Applications mobiles natives — plus tard, l'API-first les rendra possibles
- Import des référentiels partenaires (Macif, La Poste, LocalEyes, HandiPlage) — v2
- Modération avancée / back-office complet — admin minimal en v1, enrichi ensuite

## Context

### Reconstruction (sources épuisées)

Le code de production n'est plus accessible (buckets S3 supprimés, RDS mort, Wayback indisponible). La reconstitution s'appuie sur les dépôts privés encore présents :

| Source | Donnée |
|---|---|
| `jaccede-api-v4` (Flask, 2024) | Modèle `Criterion` (hiérarchique, 7 types), `Category`, `AccessibilityValue`, `OtherInformation`, importeurs partenaires |
| `commands/translations/it/*.csv` | 233 libellés critères/options, 158 catégories, 52 filtres, 16 labels TH |
| `jaccede-v3/docs/api/source/places_api.rst` | Grille **complète** de la catégorie 1 (4 groupes, 19 critères, options, types) |
| `apidocs/docs/categories.html` | 118 catégories avec libellés FR |
| `jaccede-dev-tools` + `jaccede-doc` | Confirment le dump S3 (supprimé) ; aucune donnée exploitable |

La grille fine par catégorie n'est pas récupérable à 100 % : on part de la grille catégorie 1 comme base universelle, on l'étend avec le vocabulaire et les mappings partenaires, et on rend l'ensemble **éditable en admin**.

### Environnement technique

- Monorepo : API `src/jaccede` + frontend `web/` (Next.js).
- Postgres 16 + PostGIS (géolocalisation), extensions `unaccent`.
- i18n : JSONB `{fr,en,es,de,it}` sur les libellés.
- `/Users/seb/Projects/jaccede-v5` (nouveau dépôt, GitHub Flow).

## Constraints

- **Backend** : FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic — cohérent avec l'écosystème de l'auteur.
- **Frontend** : Next.js (App Router) + TypeScript + Tailwind + MapLibre/OSM.
- **BDD** : PostgreSQL + PostGIS obligatoire (recherche géo).
- **Qualité** : ruff, mypy, bandit, pytest + coverage, pre-commit (mêmes conventions que les autres projets de l'auteur).
- **Pas de dépendance dure à Google Places** : le seed est local ; Google/OSM est un enrichissement optionnel.
- **Données historiques** : ne pas prétendre à une copie 1:1 ; conserver idées, vocabulaire et structure.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI (pas Django) | Async, OpenAPI auto, écosystème de l'auteur ; le back-office sera couvert par un admin léger | — Pending |
| Next.js (pas SvelteKit) | SEO/SSR pour un annuaire public, écosystème a11y (React Aria/shadcn), cartes | — Pending |
| PostGIS + JSONB i18n | Recherche géo native ; i18n simple sans table `Translation` | — Pending |
| Seed reconstitué (pas de dump) | Seule donnée disponible ; rendu éditable pour compléter | — Pending |
| V1 sans gamification/messagerie/mobile | Recentrage sur le cœur : référentiel + API + fiche + contribution | — Pending |

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
*Last updated: 2026-10-26 after initialization*
