# Requirements: LetMeGetIn

**Defined:** 2026-10-26
**Core Value:** Permettre à quiconque de savoir en quelques secondes si un lieu est réellement accessible, via une fiche d'accessibilité structurée et consommable par des tiers.

## v1 Requirements

### Socle & Ops

- [ ] **OPS-01**: Le projet démarre en une commande (`docker compose up` + `uv run`) avec Postgres/PostGIS
- [ ] **OPS-02**: CI exécute ruff, mypy, bandit, pytest (seuil de couverture)
- [ ] **OPS-03**: Les migrations de schéma sont gérées par Alembic

### Référentiel

- [ ] **REF-01**: L'API liste les catégories avec libellés multilingues (fr/en/es/de/it)
- [ ] **REF-02**: L'API expose l'arbre des critères par catégorie (groupes → critères → options)
- [ ] **REF-03**: L'API liste les filtres d'accessibilité (recherche) et les labels officiels
- [ ] **REF-04**: Le seed initial est chargé depuis les données reconstituées (158 catégories, 233 libellés, grille cat-1)
- [ ] **REF-05**: Un admin/CLI minimal permet d'éditer catégories, critères et options

### Lieux & recherche

- [ ] **PLACE-01**: L'utilisateur peut rechercher des lieux par texte et par proximité (lat/lng/rayon)
- [ ] **PLACE-02**: L'utilisateur peut filtrer les résultats par un ou plusieurs critères d'accessibilité
- [ ] **PLACE-03**: L'utilisateur peut consulter une fiche lieu (adresse, catégorie, note, photos)
- [ ] **PLACE-04**: La fiche lieu affiche l'arbre d'accessibilité avec les valeurs renseignées et le taux de complétude
- [ ] **PLACE-05**: Un script importe un jeu de lieux (seed local) pour peupler la recherche

### Avis & contribution

- [ ] **REV-01**: L'utilisateur peut lire les avis d'un lieu (note 1–5 + texte)
- [ ] **REV-02**: L'utilisateur authentifié peut déposer un avis
- [ ] **CONTRIB-01**: L'utilisateur authentifié peut compléter/modifier les valeurs d'accessibilité d'une fiche
- [ ] **CONTRIB-02**: Chaque contribution est journalisée et le taux de complétude est recalculé

### Auth

- [ ] **AUTH-01**: L'utilisateur peut créer un compte (email + mot de passe)
- [ ] **AUTH-02**: L'utilisateur peut se connecter et obtenir un JWT (access + refresh)
- [ ] **AUTH-03**: Les rôles `user` et `admin` contrôlent les actions sensibles

### API publique

- [ ] **API-01**: Les partenaires consomment l'API via une clé API (rate limitée)
- [ ] **API-02**: La documentation OpenAPI est générée et publiée

### Frontend

- [ ] **FRONT-01**: L'utilisateur peut rechercher des lieux (carte + liste + filtres)
- [ ] **FRONT-02**: L'utilisateur peut consulter une fiche lieu complète
- [ ] **FRONT-03**: L'utilisateur authentifié peut contribuer depuis le front
- [ ] **FRONT-04**: L'utilisateur peut gérer son compte et son profil

## v2 Requirements

### Gamification

- **GAME-01**: Challenges d'entreprise avec équipes
- **GAME-02**: Points de contribution et classements
- **GAME-03**: Messagerie d'équipe

### Intégrations

- **INTG-01**: Import des référentiels partenaires (Macif, La Poste, LocalEyes, HandiPlage)
- **INTG-02**: Enrichissement Google Places / OpenStreetMap (Overpass)
- **INTG-03**: Applications mobiles iOS/Android

## Out of Scope

| Feature | Reason |
|---------|--------|
| Copie 1:1 de la base historique | Le dump n'existe plus ; on reconstruit une grille éditable |
| Chat temps réel (Crossbar) | Complexité inutile pour le cœur référentiel |
| Applications mobiles natives | API-first d'abord, mobile ensuite |
| Back-office complet type Flask-Admin | Admin minimal en v1, enrichi selon les besoins |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| OPS-01 | Phase 1 | Pending |
| OPS-02 | Phase 1 | Pending |
| OPS-03 | Phase 1 | Pending |
| REF-01 | Phase 2 | Pending |
| REF-02 | Phase 2 | Pending |
| REF-03 | Phase 2 | Pending |
| REF-04 | Phase 2 | Pending |
| REF-05 | Phase 2 | Pending |
| PLACE-01 | Phase 3 | Pending |
| PLACE-02 | Phase 3 | Pending |
| PLACE-03 | Phase 3 | Pending |
| PLACE-04 | Phase 3 | Pending |
| PLACE-05 | Phase 3 | Pending |
| REV-01 | Phase 4 | Pending |
| REV-02 | Phase 4 | Pending |
| CONTRIB-01 | Phase 5 | Pending |
| CONTRIB-02 | Phase 5 | Pending |
| AUTH-01 | Phase 5 | Pending |
| AUTH-02 | Phase 5 | Pending |
| AUTH-03 | Phase 5 | Pending |
| API-01 | Phase 7 | Pending |
| API-02 | Phase 7 | Pending |
| FRONT-01 | Phase 6 | Pending |
| FRONT-02 | Phase 6 | Pending |
| FRONT-03 | Phase 6 | Pending |
| FRONT-04 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-26*
*Last updated: 2026-10-26 after initial definition*
