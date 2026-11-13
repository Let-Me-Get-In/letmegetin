# Phase 12: Licence provenance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-13
**Phase:** 12-licence-provenance
**Areas discussed:** Forme de la provenance, Règles de licence en données, Conflit et fraîcheur, Points d'application et refus, API publique, Affichage UI

---

## Forme de la provenance

| Option | Description | Selected |
|--------|-------------|----------|
| Colonnes dédiées | `source_license`/`source_url`/`retrieved_at` sur `place`, `source`/`source_license`/`observed_at`/`recorded_at`/`actor` sur `place_accessibility` | ✓ |
| Table d'affirmations séparée | `place_claim`, plusieurs lignes par critère, `place_accessibility` en vue résolue | |
| Rester dans le JSONB | Aucune migration, forme libre, pas d'index | |

**User's choice:** Colonnes dédiées.
**Notes:** Aucune préférence exprimée pour l'historique complet ; le journal d'écritures couvrira l'audit.

| Option | Description | Selected |
|--------|-------------|----------|
| observed_at + recorded_at | Date de la source (nullable) + date d'écriture | ✓ |
| recorded_at seulement | Une date, fraîcheur source perdue | |
| Trois dates | + retrieved_at (téléchargement) | |

**User's choice:** observed_at + recorded_at.

| Option | Description | Selected |
|--------|-------------|----------|
| actor texte | `importer:acceslibre`, `operator:<nom>`, `user:<id>` | ✓ |
| FK user_id seulement | Vide pour imports et CLI | |
| Pas d'acteur | | |

**User's choice:** actor texte.

| Option | Description | Selected |
|--------|-------------|----------|
| Backfill depuis source/JSONB | Migration déterministe, aucune ligne sans licence | ✓ |
| Seulement les nouvelles écritures | 634k lieux sans licence | |
| Ré-import complet | Rejoue tout l'import | |

**User's choice:** Backfill depuis source/JSONB.

---

## Règles de licence en données

| Option | Description | Selected |
|--------|-------------|----------|
| CSV revu + table | `licences.csv`, seed, éditable au CLI, versionné | ✓ |
| CSV lu à l'exécution | Pas de FK ni de version | |
| Enum dans le code | Viole LIC-05 | |

**User's choice:** CSV revu + table.

| Option | Description | Selected |
|--------|-------------|----------|
| Matrice explicite | `licence × destination` en données ; LIC-03 devient une ligne | ✓ |
| Attributs + logique | Flags de licence combinés en code | |
| Règle par source | Duplique la règle, ignore la re-licenciation | |

**User's choice:** Matrice explicite.

| Option | Description | Selected |
|--------|-------------|----------|
| Les 3 des exigences | `open_export`, `osm`, `lov2_partner` | ✓ |
| 3 + api + web_map | Gouverne aussi la lecture publique | |
| 3 + api | | |

**User's choice:** Les 3 des exigences.

| Option | Description | Selected |
|--------|-------------|----------|
| Snapshot sur la ligne | La copie garde la licence de l'époque | ✓ |
| Déduite à la lecture | Re-licenciation rétroactive | |
| Licence passée par l'importeur | Viole LIC-05 | |

**User's choice:** Snapshot sur la ligne.

---

## Conflit et fraîcheur

| Option | Description | Selected |
|--------|-------------|----------|
| Propriété par source | Un import ne met à jour que ses lignes ; user prend la propriété | ✓ |
| Plus frais gagne | Un import massif peut écraser une contribution | |
| Échelle de priorité | Règle en code, ignore les dates | |

**User's choice:** Propriété par source.

| Option | Description | Selected |
|--------|-------------|----------|
| Journal des écritures | `place_accessibility_write`, accepted/rejected + raison | ✓ |
| Étendre contribution | `user_id` nullable, journal hétérogène | |
| Compteurs seulement | Pas de trace après coup | |

**User's choice:** Journal des écritures.

| Option | Description | Selected |
|--------|-------------|----------|
| Comparer observed_at | Même source, entrant ≥ courant, NULL = NULL | ✓ |
| Écraser toujours | Rollback silencieux | |
| Insertion seule | Corrections de la source jamais appliquées | |

**User's choice:** Comparer observed_at.

| Option | Description | Selected |
|--------|-------------|----------|
| Insérer si absent | Compléter un critère absent, même lieu d'une autre source | ✓ |
| Rien hors de sa source | Aucune complétion croisée | |

**User's choice:** Insérer si absent.

---

## Points d'application et refus

| Option | Description | Selected |
|--------|-------------|----------|
| Domaine + SQL | Prédicat pur + même règle en SQL pour le masse | ✓ |
| Filtrage en mémoire | Charge 634k lignes avant de filtrer | |
| Chaque sortie décide | Règle réimplémentée trois fois | |

**User's choice:** Domaine + SQL.

| Option | Description | Selected |
|--------|-------------|----------|
| Exclure + compter | Manifeste par source/licence, `--verbose` liste les ids | ✓ |
| Échouer | Un lieu OSM bloque l'export | |
| Marquer et laisser passer | La donnée fuit | |

**User's choice:** Exclure + compter.

| Option | Description | Selected |
|--------|-------------|----------|
| Refus par défaut | Licence NULL/inconnue refusée partout | ✓ |
| Autoriser par défaut | Fuite silencieuse | |

**User's choice:** Refus par défaut.

| Option | Description | Selected |
|--------|-------------|----------|
| sync + matrix + audit | Même forme que `families sync\|audit` | ✓ |
| Seed seulement | Pas d'audit | |
| Pas de commande dédiée | Pas de garde-fou | |

**User's choice:** sync + matrix + audit.

---

## API publique et affichage (zones supplémentaires)

| Option | Description | Selected |
|--------|-------------|----------|
| Détail : oui | `source`/`license`/`observed_at` optionnels sur le lieu et chaque réponse | ✓ |
| Reste interne | API inchangée | |
| Lieu seulement | Pas de crédit par valeur | |

**User's choice:** Détail : oui.

| Option | Description | Selected |
|--------|-------------|----------|
| Liste inchangée | Pas de provenance dans la recherche | ✓ |
| Liste aussi | +2 champs × 100 résultats | |

**User's choice:** Liste inchangée.

| Option | Description | Selected |
|--------|-------------|----------|
| Reporter | Crédit/attribution en Phase 13 (fiche) ou 14 (EXP-02) | ✓ |
| Crédit par critère maintenant | Mélange données et UI | |
| Mention globale maintenant | C'est EXP-02 | |

**User's choice:** Reporter.

---

## Agent's Discretion

- Types de colonnes, index et ordre des colonnes CSV.
- Forme exacte du prédicat SQL (vue ou join builder), tant que le prédicat du domaine fait référence.
- Forme des compteurs de manifeste, tant qu'ils sont groupés par source/licence.

## Deferred Ideas

- Crédit de provenance par critère dans la fiche → Phase 13.
- Bloc d'attribution cumulée → Phase 14 (EXP-02).
- Provenance dans les résultats de recherche → refusée (D-17).
- Stockage de toutes les affirmations (plusieurs valeurs par critère) → refusé, journal d'écritures à la place.
