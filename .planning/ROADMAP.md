# Roadmap: LetMeGetIn

## Overview

Réécriture moderne du guide collaboratif de lieux accessibles : référentiel normalisé + API publique FastAPI + frontend Next.js. V1 = cœur produit (référentiel, recherche, fiche, contribution). Gamification, intégrations et mobile sont différés.

## Phases

### Phase 1: Socle & CI
**Goal:** Un squelette FastAPI + Postgres/PostGIS + Alembic + CI qui démarre et passe au vert.
**Mode:** mvp
**Requirements:** OPS-01, OPS-02, OPS-03
**Success Criteria**:
1. `docker compose up -d` lance PostGIS et l'API sert `GET /health` → 200.
2. `uv run alembic upgrade head` crée le schéma.
3. `uv run pytest`, `uv run ruff check .` et `uv run mypy` passent localement et en CI.

### Phase 2: Référentiel & seed
**Goal:** L'API expose catégories, critères (arbre) et filtres issus du seed reconstitué.
**Mode:** mvp
**Requirements:** REF-01, REF-02, REF-03, REF-04, REF-05
**Success Criteria**:
1. `uv run python scripts/build_referential.py` produit les JSON de seed.
2. `uv run python -m jaccede.seed` charge 158 catégories, 233 libellés et la grille catégorie 1.
3. `GET /api/v1/categories` et `GET /api/v1/categories/{slug}/criteria` répondent avec libellés multilingues.
4. `GET /api/v1/filters` renvoie les 52 filtres + labels officiels.
5. Un admin/CLI minimal permet d'ajouter/éditer un critère.

### Phase 3: Lieux & recherche
**Goal:** Rechercher des lieux par texte, proximité et filtres d'accessibilité.
**Mode:** mvp
**Requirements:** PLACE-01, PLACE-02, PLACE-03, PLACE-04, PLACE-05
**Success Criteria**:
1. Un script importe un jeu de lieux de démonstration.
2. `GET /api/v1/places?lat=&lng=&radius=&q=&filters=` renvoie des résultats triés par distance.
3. Les filtres par critère réduisent correctement les résultats.
4. `GET /api/v1/places/{slug}` renvoie la fiche complète (adresse, catégorie, note).

### Phase 4: Fiche & avis (lecture)
**Goal:** Consulter une fiche d'accessibilité complète et les avis.
**Mode:** mvp
**Requirements:** PLACE-03, PLACE-04, REV-01
**Success Criteria**:
1. La fiche renvoie l'arbre d'accessibilité (groupes → critères → options) avec valeurs.
2. Le taux de complétude (`filled_rate`) est calculé.
3. Les avis sont paginés et lisibles.

### Phase 5: Auth & contribution
**Goal:** Créer un compte, contribuer aux fiches et déposer un avis.
**Mode:** mvp
**Requirements:** AUTH-01, AUTH-02, AUTH-03, CONTRIB-01, CONTRIB-02, REV-02
**Success Criteria**:
1. Inscription + login JWT (access/refresh).
2. Un utilisateur authentifié complète une fiche → `accessibility_value` mis à jour + `contribution` journalisée.
3. Le taux de complétude est recalculé.
4. Un avis authentifié est créé.
5. Les rôles `admin` protègent l'édition du référentiel.

### Phase 6: Frontend Next.js
**Goal:** Parcours utilisateur complet (recherche, fiche, contribution, compte).
**Mode:** mvp
**Requirements:** FRONT-01, FRONT-02, FRONT-03, FRONT-04
**Success Criteria**:
1. Page d'accueil + recherche carte/liste avec filtres.
2. Fiche lieu avec arbre d'accessibilité et avis.
3. Contribution depuis le front (auth requise).
4. Gestion de compte/profil.

### Phase 7: API publique & déploiement
**Goal:** Ouvrir l'API aux partenaires et déployer.
**Mode:** mvp
**Requirements:** API-01, API-02
**Success Criteria**:
1. Une clé API authentifie et rate-limite les appels partenaires.
2. La doc OpenAPI est publiée et à jour.
3. L'application est déployée (docker/CI) et accessible.

## Progress

| Phase | Status | Completed |
|-------|--------|-----------|
| 1. Socle & CI | In progress | — |
| 2. Référentiel & seed | Pending | — |
| 3. Lieux & recherche | Pending | — |
| 4. Fiche & avis (lecture) | Pending | — |
| 5. Auth & contribution | Pending | — |
| 6. Frontend Next.js | Pending | — |
| 7. API publique & déploiement | Pending | — |

---
*Created: 2026-10-26*
