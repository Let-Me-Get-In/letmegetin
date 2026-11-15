---
phase: 14-open-odbl-export
verified: 2026-11-15T11:20:24Z
status: human_needed
score: 25/25 must-haves verified
covered_files:
  - .github/workflows/export-odbl.yml
  - .planning/phases/14-open-odbl-export/14-01-PLAN.md
  - .planning/phases/14-open-odbl-export/14-01-SUMMARY.md
  - .planning/phases/14-open-odbl-export/14-02-PLAN.md
  - .planning/phases/14-open-odbl-export/14-02-SUMMARY.md
  - .planning/phases/14-open-odbl-export/14-03-PLAN.md
  - .planning/phases/14-open-odbl-export/14-03-SUMMARY.md
  - .planning/phases/14-open-odbl-export/14-04-PLAN.md
  - .planning/phases/14-open-odbl-export/14-04-SUMMARY.md
  - .planning/phases/14-open-odbl-export/14-05-PLAN.md
  - .planning/phases/14-open-odbl-export/14-05-SUMMARY.md
  - .planning/phases/14-open-odbl-export/14-SECURITY.md
  - .planning/phases/14-open-odbl-export/14-UAT.md
  - .planning/phases/14-open-odbl-export/14-VALIDATION.md
  - data/referential/licences.csv
  - deploy/systemd/letmegetin-export-odbl-delta.service
  - deploy/systemd/letmegetin-export-odbl-delta.timer
  - deploy/systemd/letmegetin-export-odbl-snapshot.service
  - deploy/systemd/letmegetin-export-odbl-snapshot.timer
  - docker-compose.prod.yml
  - docs/deploy.md
  - docs/openapi.json
  - docs/public-api.md
  - migrations/versions/0012_export_event.py
  - migrations/versions/0013_licence_attribution_text.py
  - scripts/export-odbl.sh
  - src/letmegetin/admin.py
  - src/letmegetin/api/v1/export.py
  - src/letmegetin/api/v1/router.py
  - src/letmegetin/application/places/attribution.py
  - src/letmegetin/application/places/export.py
  - src/letmegetin/application/places/history.py
  - src/letmegetin/application/referential/licences.py
  - src/letmegetin/config.py
  - src/letmegetin/domain/places/export.py
  - src/letmegetin/domain/places/export_plan.py
  - src/letmegetin/domain/referential/entities.py
  - src/letmegetin/infrastructure/persistence/export_repositories.py
  - src/letmegetin/infrastructure/persistence/licence_repositories.py
  - src/letmegetin/infrastructure/persistence/models.py
  - src/letmegetin/infrastructure/persistence/repositories.py
  - src/letmegetin/main.py
  - tests/functional/api/test_export.py
  - tests/functional/places/test_export.py
  - tests/functional/places/test_export_event.py
  - tests/integration/api/test_openapi.py
  - tests/unit/application/places/test_export.py
  - tests/unit/application/places/test_history.py
  - tests/unit/infrastructure/persistence/test_export_event_chokepoints.py
  - tests/unit/scripts/test_export_odbl_wrapper.py
covered_digest: v4:sha256:fe8f4438a23db33c75830d27027b6f000a36b9d2911364404f4d75e1793401d4
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 25/25
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Charger les units sur l'hôte Linux : `systemd-analyze verify deploy/systemd/letmegetin-export-odbl-*.{service,timer}`, puis `systemctl enable --now letmegetin-export-odbl-snapshot.timer letmegetin-export-odbl-delta.timer` et `systemctl list-timers`."
    expected: "Aucune erreur de vérification ; snapshot dû lundi 04:00, delta quotidien 03:15 ; un run manuel via `/opt/letmegetin/scripts/with-secrets.sh` sort 0. Vérifier aussi l'absence de conflit avec `letmegetin-restore-drill.timer` (LET-125)."
    why_human: "Ce poste est sous macOS, sans systemd : les units n'ont été comparées que structurellement. LET-125 est encore en Backlog."
  - test: "Renseigner les secrets `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_SSH_KEY` et la variable `DEPLOY_HOST_FINGERPRINT`, allowlister l'IP du runner, puis lancer `.github/workflows/export-odbl.yml` en `snapshot` puis `delta`."
    expected: "Le SSH se connecte, le `case` distant accepte le mode, le wrapper écrit un ZIP et met `latest.json` à jour sans qu'aucun secret DB/API n'atteigne Actions (LET-125)."
    why_human: "Ni hôte, ni clé SSH, ni pare-feu dans le dépôt ; seul le YAML (déclencheur, secrets, `envs`, action épinglée) a pu être vérifié."
  - test: "Relire les trois `attribution_text` de `data/referential/licences.csv` (lov2, odbl, cdla) contre le texte exigé par chaque licence, et trancher le cas CDLA dont la cellule `obligations` est vide."
    expected: "Chaque phrase confirmée ou amendée ; un amendement est une revue du CSV suivie de `admin licences sync` (LET-126)."
    why_human: "Le caractère légalement exact d'une notice n'est assertable par aucun test ; 14-02 le marque `human_judgment: true`."
  - test: "Relire `## ODbL export` dans `docs/public-api.md` comme un partenaire, en particulier la portée des compteurs `excluded_*` du manifest (population courante complète, pas la fenêtre du delta)."
    expected: "La prose est acceptée comme contrat partenaire, ou corrigée sur place, avec la portée des compteurs explicitée (LET-126, point 4)."
    why_human: "Les tests épinglent les constantes et les chemins, pas le sens des paragraphes delta/compteurs."
  - test: "Trancher la question de conception laissée ouverte : `SqlAlchemyPlaceRepository.update()` journalise sans comparer pré/post."
    expected: "Soit on accepte le résidu tel quel (aucun appelant de production, rejeu idempotent, seule conséquence : un journal plus gros), soit on ajoute une comparaison pré/post avant l'append et on supprime la réserve de 14-SECURITY."
    why_human: "Aucun appelant de production aujourd'hui ; c'est un choix de coût/robustesse, pas un comportement observable en test."
---

# Phase 14 : export ODbL ouvert — rapport de vérification

**Objectif de la phase :** un partenaire peut télécharger tout le référentiel en ODbL, avec une attribution rendue dans l'export.
**Vérifié :** 2026-11-15T11:20:24Z
**Statut :** human_needed
**Re-vérification :** oui — rapport régénéré (le digest des entrées couvertes ne correspondait plus depuis `c9f6f07` et `d1992aa`)

Le verdict **change** par rapport au rapport précédent : celui-ci portait `passed` alors que son
propre bloc `human_verification` n'était pas vide, ce que la règle de décision interdit. Les
quatre points restants (systemd, run réel du workflow, revue légale, prose du contrat) sont bel et
bien ouverts — **LET-125** et **LET-126** sont en Backlog — donc le statut honnête est
`human_needed`. Aucun code n'est en cause : les 25 vérités sont vérifiées.

## Atteinte de l'objectif

### Vérités observables

| # | Vérité | Statut | Preuve |
|---|--------|--------|--------|
| 1 | `export_event` existe avec un `seq` `BigInteger IDENTITY` monotone, `xid xid8 NOT NULL DEFAULT pg_current_xact_id()` et des CHECK sur `entity` / `op` (14-01) | ✓ VÉRIFIÉE | `migrations/versions/0012_export_event.py` (colonnes, `clock_timestamp()`, les deux CHECK, index `entity_id,seq`) ; `models.py` |
| 2 | `safe_seq()` renvoie `max(seq) WHERE xid < pg_snapshot_xmin(pg_current_snapshot())` ; un événement en vol est exclu puis visible après commit (14-01) | ✓ VÉRIFIÉE | `export_repositories.py:220-231` ; `test_safe_seq_publishes_an_event_only_after_its_transaction_commits` (vert) |
| 3 | Chaque point d'écriture place journalise un événement pleine ligne dans la même transaction (add/update/merge/rejet/réassignation/dedup/réponses) ; un rejet n'écrit rien ; une écriture sans changement n'écrit rien (14-01) | ✓ VÉRIFIÉE (résidu O1) | 6 sites d'append (`repositories.py:824,888,919,1160` + `_place_update_events` sur les `UPDATE … RETURNING` aux lignes 709/751/771) ; 14 cas fonctionnels verts. **Réserve :** `update()` ajoute sans comparer pré/post (aucun appelant de production) |
| 4 | Une réponse rejetée ne reste que dans `place_accessibility_write` ; une réponse acceptée (insertion ou écrasement) journalise ; re-soumettre la même réponse n'écrit rien (14-01) | ✓ VÉRIFIÉE | 4 tests fonctionnels dédiés verts (`test_export_event.py`) |
| 5 | L'événement et l'écriture qu'il décrit sont dans la même transaction ; le repository `flush` mais ne `commit` jamais (14-01) | ✓ VÉRIFIÉE | helpers d'append sans `commit` ; `test_a_rolled_back_write_leaves_no_event_and_no_place` vert |
| 6 | `letmegetin-admin place history <slug>` affiche date, op, acteur et les champs modifiés calculés à la lecture, en ordre de `seq` (14-01) | ✓ VÉRIFIÉE | `application/places/history.py` ; 11 tests unitaires verts |
| 7 | `export odbl` écrit exactement `places.csv`, `categories.csv`, `criteria.csv`, `answers.csv`, `aliases.csv`, `ATTRIBUTION.txt`, `manifest.json` (14-02) | ✓ VÉRIFIÉE | Run indépendant sur le jeu de dev : `zf.namelist()` = exactement ces sept entrées ; `test_snapshot_zip_carries_the_seven_files…` vert |
| 8 | Chaque CSV est UTF-8, séparé par virgules, RFC 4180, ligne d'en-tête, sans BOM ; le manifest porte `schema_version`, `generated_at`, `referential_version`, les compteurs par fichier, les trois familles d'exclusions et `attribution_ref` (14-02) | ✓ VÉRIFIÉE | Run indépendant : aucun BOM sur les cinq CSV, en-têtes conformes, `manifest` relu avec exactement ces clés |
| 9 | `places.csv` ne contient que des lieux canoniques, y compris sans réponse ; un lieu fusionné n'apparaît que dans `aliases.csv` (`alias_id → canonical_id`) (14-02) | ✓ VÉRIFIÉE | Run indépendant : `626491` (sans réponse) présent ; `alias_id` ∩ `place_id` = 0 ; 5 458 alias ; test snapshot vert |
| 10 | La réponse d'un lieu fusionné est réécrite sur l'id canonique, classée canonique-d'abord puis `recorded_at DESC`, `place_id DESC`, `criterion_id DESC`, chaque perdant compté par source+licence (14-02) | ✓ VÉRIFIÉE | `_ranked_answers` (`export_repositories.py:96-133`) ; `test_answer_precedence…` et test snapshot verts |
| 11 | Une réponse n'entre dans `answers.csv` que si sa propre licence **et** celle de son lieu canonique autorisent `open_export` ; les réponses retenues sont absentes et comptées ; les trois populations se réconcilient (14-02) | ✓ VÉRIFIÉE | `_answer_may_leave` / `_licence_allows` (SQL, fail-closed) ; run indépendant : 1 702 243 réponses exportées + 8 852 exclues (`acceslibre/lov2`) ; `test_the_exported_plus_excluded_plus_withheld_answers_reconcile` vert |
| 12 | `answers.csv` est indexé par `(place_id, criterion_slug)` ; chaque ligne porte `source`, `source_license`, `source_url` (nullable) et la date source-d'abord (14-02) | ✓ VÉRIFIÉE (réserve O2 pour `places.csv`) | Run indépendant : 1 702 243 clés, unicité vérifiée ; en-têtes conformes ; dates des réponses présentes. **Réserve :** `date` vide sur les 629 473 lignes de `places.csv` (voir O2) |
| 13 | `ATTRIBUTION.txt` ne liste que les sources réellement présentes, avec nom légal et phrase de `data/referential/licences.csv`, la phrase Produced Works et la phrase prospective, répétées à l'identique dans `manifest.attribution` ; aucune colonne par ligne, aucune ligne OSM/Overture codée en dur (14-02) | ✓ VÉRIFIÉE | Run indépendant : une seule ligne `acceslibre — Licence Ouverte v2.0 (Etalab 2.0) — 2026-11-13 — « Source » : …` + les deux constantes ; `manifest.attribution == contenu du fichier` |
| 14 | `latest.json` porte `snapshot {name, seq}`, `watermark`, `retention_floor_seq`, `deltas[]` ; un delta ne publie que `watermark < seq <= safe_seq()` ; le watermark ne bouge qu'après écriture+fsync du ZIP ; `--since` sous le plancher est refusé en nommant le plancher et le snapshot (14-02) | ✓ VÉRIFIÉE | Run indépendant : forme exacte ; delta ajouté à `deltas[]` sans toucher `snapshot`/`watermark` ; `--since -5` → exit 1, message nommant le plancher 0 et le snapshot ; `--delta --since` → exit 1 ; 4 tests dédiés verts |
| 15 | La rétention élague `export_event` à la borne du snapshot précédent, supprime les deltas subsumés et les orphelins, garde les snapshots, et n'élague rien si le snapshot échoue (14-02) | ✓ VÉRIFIÉE | `_prune_deltas` + `delete_up_to(previous[1])` ; `test_retention_prunes_to_the_previous_snapshot…` et `test_a_failed_snapshot_prunes_nothing` verts |
| 16 | `GET /api/v1/export/latest.json` sert l'index écrit par le CLI, 404 s'il manque ou est illisible, sous la limite anonyme (14-03) | ✓ VÉRIFIÉE | `api/v1/export.py:21-37` ; 3 tests de route verts |
| 17 | `GET /api/v1/export/{name}.zip` sert une archive et refuse séparateurs, `..`, fichiers cachés, `.lock`, `.tmp`, les liens sortants **et tout caractère non imprimable** ; fichier absent = 404 (14-03, LET-128) | ✓ VÉRIFIÉE | `api/v1/export.py:52-77` + `_is_servable` (`filename.isprintable()`) ; 9 URL de traversée + symlink + cas d'aide verts ; sonde live : `x%00.zip` → 404 |
| 18 | Le répertoire d'export est un volume nommé `export_data` monté en lecture seule à `LETMEGETIN_EXPORT_DIR` dans `api`, partagé avec la génération hôte (14-03) | ✓ VÉRIFIÉE | `docker-compose.prod.yml:68` (`export_data:/data/export:ro`), env `/data/export`, volume déclaré ligne 131 |
| 19 | `docs/public-api.md` documente les deux routes, les sept entrées/colonnes, les ids d'origine par fichier, le contrat delta MVCC, l'allow-list du garde CSV, l'`attribution_text` par licence et la phrase Produced Works (14-04) | ✓ VÉRIFIÉE | `docs/public-api.md:154-330` lu intégralement ; `test_openapi_exposes_the_public_contract` vert |
| 20 | Les phrases Produced Works et prospective des docs sont les constantes partagées de `application/places/attribution.py`, identiques à `ATTRIBUTION.txt` (14-04) | ✓ VÉRIFIÉE | `test_public_api_documents_the_shared_attribution_sentences` vert ; run indépendant : les deux phrases présentes dans le ZIP |
| 21 | `docs/openapi.json` est régénéré (jamais édité à la main) et porte les deux chemins d'export (14-04) | ✓ VÉRIFIÉE | `app.openapi()` comparé octet à octet au fichier : identique, sha256 `f49d7a1b5a162612…` |
| 22 | `scripts/export-odbl.sh {snapshot|delta}` construit l'argv exact avec un seul `$OUT`, `run --rm -T`, un volume inscriptible sur un second point de montage, `--delta` seulement en delta, aucun `jq`/`--since`, exit 2 sur un mode inconnu (14-05) | ✓ VÉRIFIÉE | `scripts/export-odbl.sh` ; 3 tests wrapper verts (un `docker` factice capture l'argv, un `jq` factice prouve qu'il n'est jamais appelé) |
| 23 | Un snapshot hebdomadaire (lun. 04:00) et un delta quotidien (03:15) sont quatre units systemd distinctes pilotées par `with-secrets.sh` (14-05) | ✓ VÉRIFIÉE (structurel) | Les 4 fichiers lus : `OnCalendar=Mon *-*-* 04:00:00` / `*-*-* 03:15:00`, `ExecStart=… with-secrets.sh … export-odbl.sh {snapshot|delta}`. Chargement sur Linux = humain |
| 24 | Un workflow `workflow_dispatch` se connecte en SSH à l'hôte, lance le même wrapper avec le mode choisi, et ne porte aucun secret DB/API (14-05) | ✓ VÉRIFIÉE (structurel) | `.github/workflows/export-odbl.yml` : `workflow_dispatch` + `choice [delta, snapshot]`, action épinglée par SHA, `permissions: contents: read`, trois `DEPLOY_*`, `envs: MODE=…`, `case snapshot|delta` distant. Run réel = humain |
| 25 | `docs/deploy.md` montre les lignes exactes des units, la commande de génération inscriptible, le delta MVCC vs `--since`, les prérequis Actions et l'allowlist du runner, la rétention automatique et l'import AccesLibre atomique (14-05) | ✓ VÉRIFIÉE | `docs/deploy.md:120-215` lu ; `data/export-rw`, les deux `OnCalendar`, `ExecStart=`, allowlist, rétention, atomicité présents |

**Score :** 25/25 vérités vérifiées (0 présente-mais-non-exercée)

### Durcissements postérieurs au rapport précédent

Deux corrections ont atterri après la dernière vérification. Chacune a été re-testée ici, et chaque
test a été rejoué **sans** la correction dans un worktree jetable, pour prouver qu'il échoue (aucun
fichier d'implémentation n'a été modifié dans l'arbre de travail).

| # | Comportement | Test | Échoue sans la correction ? | Statut |
|---|---|---|---|---|
| H1 | `export odbl` refuse d'écrire quand la matrice de licences revue est vide, et nomme `admin licences sync` (`c9f6f07`) | `tests/unit/application/places/test_export.py::test_an_empty_licence_matrix_refuses_to_write_a_silently_empty_export` | Oui — `AttributeError: 'NoneType' object has no attribute 'safe_seq'` (le garde se trouve avant `safe_seq()`) | ✓ |
| H2 | `_is_servable` refuse tout caractère non imprimable, donc un nom portant un octet NUL répond 404 au lieu de faire lever `Path.resolve()` (`d1992aa`, LET-128) | `tests/functional/api/test_export.py::test_only_a_plain_zip_name_is_servable[export-2026\x0011.zip-False]` | Oui — la fonction renvoie `True` sans `filename.isprintable()` | ✓ |

Le garde H1 s'appuie sur `licence_rules_count()` (nouvelle méthode du port
`ExportPlanRepository`, implémentée sur `licence_destination`, la table que `_licence_allows`
interroge réellement) ; il est placé après `begin_repeatable_read()` et avant `safe_seq()`, donc il
s'applique aussi à un delta et à un `--since`, et n'écrit rien avant de lever.

**Faiblesses de ces deux tests (non bloquantes) :** le test H1 échoue sans la correction par une
`AttributeError`, pas par l'écriture d'un export vide — il pinne la *position* du garde, pas la
sémantique « matrice vide ». Le test H2 est au niveau de l'aide `_is_servable`, pas de la route :
le cas route `%00` a été vérifié **à la main** (404 sur `x%00.zip` et `export-2026%0011.zip`), mais
aucun cas de régression route-level ne le fige. Voir O5.

### Critères de succès ROADMAP

| # | Critère | Statut | Preuve |
|---|---------|--------|--------|
| 1 | Un partenaire télécharge un export ODbL des lieux, catégories, critères et réponses, chaque ligne portant un id stable et son id d'origine | PRÉSENT | ZIP réel : `places.csv` 629 473, `categories.csv` 158, `criteria.csv` 61, `answers.csv` 1 702 243 ; `place_id` + `origin_id`/`(source, source_id)`, `(place_id, criterion_slug)`, `slug` des catégories/critères |
| 2 | L'export rend une attribution ne listant que les sources présentes, avec les noms légaux lus dans `licences.csv` (AccesLibre avec nom de source et date de mise à jour) | PRÉSENT | `ATTRIBUTION.txt` : `acceslibre — Licence Ouverte v2.0 (Etalab 2.0) — 2026-11-13 — « Source » : …`, aucune ligne OSM/Overture. La validité légale de la phrase reste humaine (LET-126) |
| 3 | L'API et la carte sont documentées comme Produced Works à côté de l'export | PRÉSENT | `PRODUCED_WORKS_SENTENCE` dans `attribution.py`, `ATTRIBUTION.txt`, `manifest.attribution` et `docs/public-api.md`, épinglée par un test d'intégration |

### Éléments différés

Aucun. Aucun des points restants n'est couvert par une phase ultérieure du jalon : les phases 15 à
17 traitent du round-trip AccesLibre, d'OSM et d'Overture, pas du chargement des timers, du run réel
du workflow, ni de la revue légale.

### Artefacts requis

| Artefact | Attendu | Statut | Détails |
|----------|---------|--------|---------|
| `migrations/versions/0012_export_event.py` | journal avec `seq` identity, `xid8`, CHECK | ✓ VÉRIFIÉE | Migration appliquée ; base de test à `0013 (head)` |
| `migrations/versions/0013_licence_attribution_text.py` | colonne additive nullable | ✓ VÉRIFIÉE | Pas de backfill : le CSV reste la source |
| `src/letmegetin/domain/places/export.py` | port d'événement, `describe_changes`, `_jsonable` fail-closed | ✓ VÉRIFIÉE | Cas unitaire « non fini » vert |
| `src/letmegetin/domain/places/export_plan.py` | dataclasses de ligne, sérialiseurs CSV, garde, manifest, `licence_rules_count` (port) | ✓ VÉRIFIÉE | 15 tests unitaires verts |
| `src/letmegetin/application/places/export.py` | cas d'usage snapshot/delta/catch-up, flock, `latest.json` atomique, rétention, garde matrice vide | ✓ VÉRIFIÉE | Tests fonctionnels + run indépendant |
| `src/letmegetin/application/places/attribution.py` | rendu des sources présentes + constantes partagées | ✓ VÉRIFIÉE | Utilisé par l'export et par le test des docs |
| `src/letmegetin/infrastructure/persistence/export_repositories.py` | `safe_seq`, `seq_at_or_before`, `delete_up_to`, `licence_rules_count`, lectures streamées, compteurs | ✓ VÉRIFIÉE | Aucun `commit` dans le repository |
| `src/letmegetin/infrastructure/persistence/repositories.py` | append du journal dans la même transaction à chaque point d'écriture | ✓ VÉRIFIÉE | 14 cas fonctionnels + test AST de recensement |
| `src/letmegetin/api/v1/export.py` | deux routes en lecture seule, limite anonyme, garde de traversée + caractères non imprimables | ✓ VÉRIFIÉE | 28 tests fonctionnels verts |
| `src/letmegetin/admin.py` | `export odbl --out [--delta] [--since]`, `place history` | ✓ VÉRIFIÉE | CLI invoqué en test fonctionnel ; `bump=False`, exit 1 sur `DomainError` (vérifié) |
| `scripts/export-odbl.sh` | wrapper snapshot/delta, second montage inscriptible | ✓ VÉRIFIÉE | `bash -n` + test d'argv + shim `jq` |
| `deploy/systemd/letmegetin-export-odbl-{snapshot,delta}.{service,timer}` | units hebdo/quotidiennes | ✓ VÉRIFIÉE (structurel) | Chargement sur Linux = humain (LET-125) |
| `.github/workflows/export-odbl.yml` | `workflow_dispatch` SSH, aucun secret DB/API | ✓ VÉRIFIÉE (structurel) | Run réel = humain (LET-125) |
| `data/referential/licences.csv` | `attribution_text` revu | ✓ VÉRIFIÉE pour la présence et l'usage | Exactitude légale = humain (LET-126) |
| `docs/public-api.md`, `docs/openapi.json`, `docs/deploy.md` | contrat partenaire + ops | ✓ VÉRIFIÉE | Lus ; OpenAPI octet-identique |

### Liens clés

| De | Vers | Via | Statut | Détails |
|----|------|-----|--------|---------|
| `can_redistribute` (domaine) | `_licence_allows` / `_answer_may_leave` (SQL) | `EXISTS` sur `licence_destination` | CÂBLÉ | Même matrice des deux côtés ; tests d'accord et de rétention |
| Dataclasses de `ExportPlan` | `csv.writer` | `serialise_rows` / `_write_csv_entry` | CÂBLÉ | RFC 4180 en unitaire + ZIP fonctionnel |
| `COALESCE(place.canonical_id, place.id)` | `place_id` de `answers.csv` | CTE `ranked_answers` | CÂBLÉ | Réponse fusionnée émise sous l'id canonique |
| `safe_seq()` | borne et lignes streamées | transaction `REPEATABLE READ`, `safe_seq()` en premier | CÂBLÉ | Tests de fenêtre et d'absence de trou |
| `licence_rules_count()` | garde d'export | `export_odbl` avant `safe_seq()` | CÂBLÉ | Test H1 + run réel (matrice à 9 lignes) |
| `delete_up_to(previous_snapshot.seq)` | élagage du journal | étape de rétention d'`export_odbl` | CÂBLÉ | Tests rétention et snapshot échoué |
| `scripts/export-odbl.sh <mode>` | `letmegetin-admin export odbl --out … [--delta]` | argv `compose run` | CÂBLÉ | Test d'argv exact |
| volume `export_data` | wrapper `/data/export-rw` ↔ API `/data/export` | volume nommé Compose | CÂBLÉ | Cible `:ro` dans l'API, cible inscriptible côté wrapper |
| constantes d'`attribution.py` | `docs/public-api.md` | assertion d'intégration | CÂBLÉ | Test vert |

### Trace de flux de données (niveau 4)

Run indépendant de bout en bout sur le jeu de dev complet (base `letmegetin`, 634 931 lieux,
1 711 095 réponses), CLI réel, répertoire temporaire :

| Artefact | Variable | Source | Données réelles | Statut |
|----------|----------|--------|-----------------|--------|
| `places.csv` | champs du lieu, `source_license`, `date` | `PlaceModel` via lecture streamée (`yield_per=1000`) | Oui — 629 473 lignes, ids d'origine UUID | ✓ FLUIDE |
| `answers.csv` | gagnant par `(canonical_id, criterion_id)` | CTE `_ranked_answers` sur `place_accessibility` | Oui — 1 702 243 clés uniques | ✓ FLUIDE |
| `aliases.csv` | `alias_id`, `canonical_id` | `place.canonical_id IS NOT NULL` | Oui — 5 458 alias, aucun id alias dans `places.csv` | ✓ FLUIDE |
| `ATTRIBUTION.txt` | source/licence/date/phrase | `(source, source_license)` des lignes exportées + `licences.csv` | Oui — seul `acceslibre/lov2` présent | ✓ FLUIDE |
| `manifest.json` | compteurs, exclusions | compteurs SQL sur la population courante | Oui — 8 852 réponses exclues (`acceslibre/lov2`) | ✓ FLUIDE |
| `latest.json` | snapshot/watermark/plancher/deltas | `safe_seq()` + état précédent du fichier | Oui — delta ajouté, snapshot inchangé | ✓ FLUIDE |
| `/api/v1/export/*` | index/archive servis | fichiers écrits par le CLI dans `settings.export_dir` | Oui — routes testées sur un répertoire réel | ✓ FLUIDE |

### Contrôles comportementaux

| Comportement | Commande | Résultat | Statut |
|--------------|----------|----------|--------|
| Snapshot complet réel (objectif de la phase) | `uv run python -m letmegetin.admin export odbl --out <tmp>` | 44,6 s, ZIP de 54 989 030 octets, sept entrées, compteurs conformes à l'UAT | ✓ PASSE |
| Delta sur le même répertoire | `… export odbl --out <tmp> --delta` | `deltas[]` gagne `{from_seq: 0, to_seq: 0}`, `snapshot` et `watermark` intacts | ✓ PASSE |
| Refus sous le plancher | `… export odbl --out <tmp> --since -5` | exit 1, message nommant le plancher 0 et le snapshot de départ | ✓ PASSE |
| Exclusivité `--delta`/`--since` | `… export odbl --out <tmp> --delta --since 3` | exit 1 | ✓ PASSE |
| Routes d'export | `uv run pytest tests/functional/api/test_export.py -q` | 28 passés (9 traversées + symlink + 10 cas d'aide + NUL + rate limit + OpenAPI) | ✓ PASSE |
| Export fonctionnel | `uv run pytest tests/functional/places/test_export.py -q` | 9 passés | ✓ PASSE |
| Journal fonctionnel | `uv run pytest tests/functional/places/test_export_event.py -q` | 14 passés | ✓ PASSE |
| Suites unitaires/intégration de la phase | 5 fichiers | 15 + 11 + 3 + 3 + 3 passés | ✓ PASSE |
| Suite complète (claim de 14-VALIDATION) | `uv run pytest -q` | 486 passés en 137,97 s | ✓ PASSE |
| OpenAPI déterministe | `app.openapi()` vs `docs/openapi.json` | Identique, sha256 `f49d7a1b5a162612…` | ✓ PASSE |
| Garde H1 sans la correction | worktree jetable, garde retiré | `AttributeError` → test rouge | ✓ PASSE |
| Garde H2 sans la correction | worktree jetable, `isprintable` retiré | `_is_servable` renvoie `True` → test rouge | ✓ PASSE |
| NUL au niveau route (live) | `TestClient`, `x%00.zip` et `export-2026%0011.zip` | 404 avec `{"detail": "Export not available"}` | ✓ PASSE |
| Traversées au niveau route (live) | 9 URL de `test_export.py` | 404 partout | ✓ PASSE |

### Exécution des probes

Aucune. La phase ne déclare ni ne contient de `scripts/*/tests/probe-*.sh` ; l'export est exercé par
la suite fonctionnelle et par le run indépendant ci-dessus.

### Couverture des exigences

| Exigence | Plans source | Description | Statut | Preuve |
|----------|--------------|-------------|--------|--------|
| EXP-01 | 14-01, 14-02, 14-03, 14-05 | Télécharger un export ODbL des lieux, catégories, critères et réponses, avec ids stables et ids d'origine | ✓ SATISFAITE | ZIP réel à sept entrées ; quatre familles de lignes ; ids stables + ids d'origine ; delta/catch-up ; service en lecture seule ; wrapper hôte |
| EXP-02 | 14-02, 14-04 | L'attribution liste les sources présentes ; l'API et la carte sont documentées comme Produced Works | ✓ SATISFAITE | `ATTRIBUTION.txt` présent-sources + `manifest.attribution` ; constantes partagées dans les docs et le ZIP. La revue légale reste humaine |

Aucune exigence orpheline : `.planning/REQUIREMENTS.md` mappe exactement EXP-01 et EXP-02 à la
phase 14, et les cinq plans les déclarent (`[EXP-01]`, `[EXP-01, EXP-02]`, `[EXP-01]`, `[EXP-02]`,
`[EXP-01]`).

### Couverture des décisions

`check.decision-coverage-verify` : 16 décisions trackables, 16 honorées, aucune non honorée.

### Audit qualité des tests

| Fichier de test | Exigence | Actifs | Ignorés | Circulaire | Niveau d'assertion | Verdict |
|-----------------|----------|--------|---------|------------|--------------------|---------|
| `tests/functional/api/test_export.py` | EXP-01 | 28 | 0 | non | Valeur + comportement (corps, media type, markeur absent) | ✓ |
| `tests/functional/places/test_export.py` | EXP-01, EXP-02 | 9 | 0 | non | Comportement (ZIP relu, réconciliation des compteurs) | ✓ |
| `tests/functional/places/test_export_event.py` | EXP-01 | 14 | 0 | non | Comportement (rollback/commit, visibilité MVCC) | ✓ |
| `tests/unit/application/places/test_export.py` | EXP-01, EXP-02 | 15 | 0 | non | Valeur (CSV, manifest, garde, garde matrice vide) | ✓ |
| `tests/unit/application/places/test_history.py` | EXP-01 | 11 | 0 | non | Valeur (ordre, résumé des champs) | ✓ |
| `tests/unit/infrastructure/persistence/test_export_event_chokepoints.py` | EXP-01 | 3 | 0 | non | Structure (recensement AST des écrivains) | ✓ |
| `tests/unit/scripts/test_export_odbl_wrapper.py` | EXP-01 | 3 | 0 | non | Valeur (argv exact, exit 2) | ✓ |
| `tests/integration/api/test_openapi.py` | EXP-02 | 3 | 0 | non | Valeur (constantes partagées dans la prose) | ✓ |

**Tests désactivés sur une exigence :** 0. **Motifs circulaires :** 0. **Assertions
insuffisantes :** 0 sur les exigences. Le seul `skipif` du dépôt est dans
`tests/unit/scripts/test_build_referential.py`, hors périmètre.

### Anti-patrons

| Fichier | Ligne | Motif | Gravité | Impact |
|---------|-------|-------|---------|--------|
| les 50 entrées couvertes | — | Aucun `TBD` / `FIXME` / `XXX` / `TODO` / `HACK` | — | Aucun |
| — | — | Aucun retour stub, aucune génération par requête, aucune ligne OSM/Overture codée en dur, aucune colonne d'attribution par ligne | — | Aucun |

### Cohérence de `14-VALIDATION.md`

`14-VALIDATION.md` est globalement exact — 486 tests collectés et verts, pytest 9.1.1, ~135 s
(137,97 s mesurés), tous les fichiers de test cités existent, chaque exigence (EXP-01, EXP-02) mappe
à au moins une commande, et les quatre éléments « manual-only » correspondent aux points humains de
ce rapport. Trois lignes de la carte de vérification ne sont toutefois **pas** couvertes par la
commande qu'elles citent :

1. **14-05-02** (« Actions ne porte aucun secret DB/API ») et **14-05-03** (« le runbook correspond
   aux units et au montage inscriptible ») pointent vers
   `tests/unit/scripts/test_export_odbl_wrapper.py`. Ce fichier n'asserte que l'argv du wrapper : il
   ne lit ni `.github/workflows/export-odbl.yml`, ni `docs/deploy.md`. Ces deux vérifications sont
   structurelles et ont été faites à la main par le vérificateur, pas par un test.
2. **14-03-02** (« le volume est en lecture seule dans le service api ») est typé « functional
   (compose assertion) » et pointe vers `tests/functional/api/test_export.py`. Aucun test du dépôt
   n'ouvre `docker-compose.prod.yml` : l'assertion compose a été faite par `docker compose config`
   en vérification.
3. **14-02-01** décrit un test unitaire couvrant « answer licence filter is fail-closed ». Ce
   filtre vit dans le SQL (`_licence_allows` / `_answer_may_leave`) et n'est couvert que par les
   tests fonctionnels ; le fichier unitaire couvre le plan, les sérialiseurs et le garde CSV.

Aucune de ces trois lignes ne change le verdict : les comportements sont vérifiés, mais par une
assertion de vérificateur ou un test fonctionnel, pas par la commande déclarée.

### Observations (résiduelles, non bloquantes)

- **O1 — `update()` journalise sans comparer pré/post.** La clause « une écriture sans changement
  n'écrit rien » du must-have 14-01 tient pour `set_review_state` et `upsert_accessibility`
  (testée), mais pas pour `SqlAlchemyPlaceRepository.update()`, qui réassigne tous les champs puis
  appelle `_append_export_event` sans comparaison. Aucun appelant de production (seuls les tests
  `_rename` l'utilisent) ; la conséquence serait un journal plus gros, jamais une erreur de contenu
  (le rejeu est un upsert de ligne complète). Déjà consigné comme réserve dans `14-SECURITY.md`.
  Décision demandée en vérification humaine.
- **O2 — `date` vide sur toutes les lignes de `places.csv`.** Dans le jeu de dev,
  `place.observed_at` et `place.retrieved_at` sont NULL sur les 634 931 lignes ; la règle
  `observed_at else retrieved_at` est donc correcte mais ne produit rien, alors que
  `docs/public-api.md` annonce « sinon notre heure de récupération ». L'importeur écrit pourtant
  `retrieved_at` (`import_acceslibre.py:283`) : le jeu de données a été chargé avant, ou par un
  autre chemin. Aucun critère de succès ni exigence ne porte sur les dates. À traiter soit par un
  ré-import, soit par un ajustement de la phrase des docs (LET-126).
- **O3 — les compteurs `excluded_*` du manifest portent sur la population courante, même dans un
  delta**, alors que les lignes et `files` sont fenêtrés. Le run indépendant le montre (8 852
  exclus dans un delta qui ne contient aucune ligne). `docs/public-api.md` ne le dit pas encore ;
  c'est exactement le point 4 de LET-126.
- **O4 — le libellé de source dans l'attribution est le slug (`acceslibre`)**, pas un nom
  d'affichage. Le nom légal de la licence et la date sont présents ; un libellé casé demanderait
  un champ de données revu.
- **O5 — les tests route de traversée acceptent `400/404/422`** alors que le contrat documenté est
  404. En pratique, les 9 URL et le cas NUL répondent tous 404 (vérifié live) : c'est une
  tolérance de test, pas un écart de comportement. Aucun cas route-level ne fige le `%00`.
- **O6 — le plan 14-05 est en retard sur le code** : il décrit encore `-v export_data:/data/export`
  et `--out /data/export`, alors que le wrapper livre `/data/export-rw` (même volume, second point
  de montage inscriptible). `14-05-SUMMARY.md` documente l'écart et la raison (Compose ajoute les
  montages `run -v` et ne peut pas relâcher le `:ro`). L'assertion de doc du Summary cherche la
  sous-chaîne `run --rm -T -v export_data:/data/export`, qui matche aussi `/data/export-rw` : elle
  passerait pour l'ancien chemin.
- **O7 — `14-SECURITY.md` précède LET-128.** La mitigation de T-14-07 décrit l'allow-list de noms
  et la contention de chemin résolu, mais pas le refus des caractères non imprimables, arrivé
  après (11:59 contre 09:58). Le registre reste exact, simplement incomplet sur ce durcissement.
- **O8 — `14-UAT.md` garde `status: testing`** dans son frontmatter alors que les 10 tests sont
  `pass`, `issues: 0`, `pending: 0`, et que l'unique écart (G-14-7, octet NUL) est marqué
  `resolved` par LET-128.
- **O9 — le prérequis opérateur `admin licences sync` n'apparaît pas dans `docs/deploy.md`.** Après
  une base neuve, l'export échoue désormais avec un message explicite (H1), mais le runbook ne
  mentionne pas l'étape. Le message d'erreur suffit à l'opérateur ; l'ajout au runbook serait une
  ligne.

### Vérification humaine requise

1. **Charger les units systemd sur l'hôte Linux** (LET-125)

   **Test :** `systemd-analyze verify deploy/systemd/letmegetin-export-odbl-*.{service,timer}`, puis
   `systemctl enable --now letmegetin-export-odbl-snapshot.timer letmegetin-export-odbl-delta.timer`
   et `systemctl list-timers` ; vérifier l'absence de conflit avec `letmegetin-restore-drill.timer`.
   **Attendu :** aucune erreur ; snapshot dû lundi 04:00, delta quotidien 03:15 ; un run manuel via
   `with-secrets.sh` sort 0.
   **Pourquoi humain :** macOS n'a pas systemd ; seule une comparaison structurelle a été possible.

2. **Lancer le workflow contre le vrai hôte** (LET-125)

   **Test :** renseigner `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` et
   `DEPLOY_HOST_FINGERPRINT`, allowlister l'IP du runner, dispatcher `snapshot` puis `delta`.
   **Attendu :** le SSH se connecte, le `case` distant accepte le mode, le wrapper écrit dans
   `export_data:/data/export-rw`, et `latest.json` / le ZIP servi se mettent à jour.
   **Pourquoi humain :** aucun hôte, aucune clé, aucun pare-feu dans le dépôt ; seuls la forme du
   YAML, le déclencheur, les secrets et le format `envs` ont été vérifiés.

3. **Relire légalement l'attribution** (LET-126)

   **Test :** comparer les trois `attribution_text` de `data/referential/licences.csv` au texte
   exigé par chaque licence, et trancher le cas CDLA (obligation d'attribution alors que la cellule
   `obligations` est vide).
   **Attendu :** phrases confirmées ou amendées ; un amendement = revue du CSV + `admin licences sync`.
   **Pourquoi humain :** jugement légal, non testable ; 14-02 le marque `human_judgment: true`.

4. **Relire la prose du contrat partenaire** (LET-126)

   **Test :** lire `## ODbL export` dans `docs/public-api.md` contre le comportement livré, en
   particulier la portée des compteurs `excluded_*` (O3) et la phrase sur la date de lieu (O2).
   **Attendu :** prose acceptée ou corrigée sur place.
   **Pourquoi humain :** les tests épinglent constantes et chemins, pas le sens des paragraphes.

5. **Trancher le résidu `update()`** (décision de conception, O1)

   **Test :** décider d'accepter le résidu (aucun appelant de production, rejeu idempotent) ou
   d'ajouter une comparaison pré/post avant l'append dans `SqlAlchemyPlaceRepository.update()` et de
   retirer la réserve correspondante de `14-SECURITY.md`.
   **Attendu :** une décision explicite, consignée.
   **Pourquoi humain :** choix de coût/robustesse, sans comportement observable aujourd'hui.

### Synthèse des écarts

Aucun must-have échoué, aucun artefact manquant, aucun lien cassé, aucun blocker d'anti-patron. Le
code livré tient l'objectif : un run réel sur le jeu complet produit le ZIP à sept entrées, les
règles de remap/licence/attribution s'appliquent, la borne MVCC et la rétention se comportent comme
décrit, les routes servent en lecture seule et résistent à la traversée comme aux caractères non
imprimables, et le wrapper/les timers/le workflow existent. Les deux corrections postérieures au
rapport précédent sont couvertes par des tests qui échouent sans elles.

Le statut est **`human_needed`**, et non `passed` : quatre points exigent un hôte Linux ou un
jugement légal (LET-125, LET-126, tous deux en Backlog), un cinquième demande une décision de
conception (O1). Aucun de ces points n'est un écart de code observable sur cette machine.

---

_Vérifié : 2026-11-15T11:20:24Z_
_Vérificateur : l'agent (gsd-verifier)_
