# Deux propositions à AccesLibre : doublons et SIRET

Ce document contient les textes à poster sur leur dépôt
(`github.com/MTES-MCT/acceslibre`) et les chiffres qui les appuient. Les mesures
portent sur l'export `acceslibre.csv` du 17 novembre 2026 (635 173 ERP) et sur
leur code au relevé `1ce90745`.

Rien ici n'est une écriture dans leur base ni dans leur dépôt : ce sont deux
propositions, chacune avec un livrable qu'ils peuvent ignorer.

---

## 1. Doublons — proposition d'issue

**Titre :** Conserver la trace des fusions et publier un indicateur de doublon

**Corps :**

> Bonjour,
>
> En réutilisant l'export Etalab, nous avons mesuré combien de doublons
> subsistent après votre passe `remove_duplicates`. Méthode : rapprochement par
> `rnb_id`, par adresse (`numero` + `voie` + commune) et par nom normalisé, dans
> un rayon de 50 m, sur les 635 173 ERP de l'export du 17 novembre.
>
> Résultat reproductible (script joint, aucune écriture) :
>
> - 3 200 paires dans le **même bâtiment** (`rnb_id` identique) avec un nom proche ;
> - 2 434 paires à la **même adresse exacte** alors que le `rnb_id` manque d'un côté ;
> - 2 829 paires sans preuve, à examiner ;
> - 950 paires écartées parce que les deux `rnb_id` connus sont **différents** — ce
>   sont les faux positifs qu'une déduplication par le nom seul produirait.
>
> Deux remarques, plus importantes que les chiffres :
>
> 1. `remove_duplicates` **supprime** la fiche absorbée. Une fois l'export publié,
>    plus rien ne permet de savoir qu'une fiche en a remplacé une autre : ni pour
>    contester la fusion, ni pour récupérer un champ perdu. Un `duplicate_of` (id de
>    la fiche conservée) ou une table de correspondance suffirait, sans changer
>    votre modèle.
> 2. La règle actuelle (même commune, nom identique, 75 m — ou 500 m si
>    `check_for_automatic_merge` passe) laisse passer les variantes de graphie et les
>    écarts d'adresse. Les 5 634 paires ci-dessus sont précisément celles que la
>    règle ne voit pas.
>
> Nous pouvons fournir le CSV complet (identifiants, verdict, score, distance,
> adresse et `rnb_id` des deux côtés) si cela vous est utile, et nous pouvons
> adapter le format à ce que vous préférez. Ce n'est pas une critique de la passe
> existante : c'est la mesure de ce qu'elle ne peut pas voir sans identifiant de
> bâtiment.

**Script :** `scripts/acceslibre_duplicate_candidates.py` (stdlib, 30 s sur
l'export national) :

```bash
uv run python scripts/acceslibre_duplicate_candidates.py acceslibre.csv candidats.csv
```

---

## 2. SIRET — proposition d'issue

**Titre :** SIRET : le champ est à 1 %, et un rapprochement automatique serait risqué

**Corps :**

> Bonjour,
>
> Le `siret` est renseigné sur **1,0 %** des 635 173 ERP de l'export (contre 56 %
> pour `rnb_id`). C'est un champ déclaré, généralement au moment où un
> propriétaire revendique sa fiche, et il reste donc très minoritaire.
>
> Nous avons testé un enrichissement automatique contre l'API Recherche
> d'entreprises, en filtrant sur le code postal et en comparant le nom : 4
> correspondances acceptées sur 40 fiches testées, avec des faux évidents dès
> qu'on relâche la règle (un cimetière rapproché d'une marbrerie, une école
> maternelle d'une mairie). Un rapprochement par le nom seul serait dangereux et
> produirait des SIRET faux, difficiles à corriger ensuite.
>
> Ce qui nous semble utile, dans l'ordre :
>
> 1. **Demander le SIRET au moment de la revendication** (et le valider par la
>    clé Luhn + l'API Sirene). C'est le seul levier qui fasse passer le taux de 1 %
>    à quelque chose d'exploitable.
> 2. **Rapprochement en masse contre Sirene** (INSEE, Licence Ouverte), avec une
>    exigence d'adresse : même numéro, même voie, même commune. Le nom seul ne
>    suffit pas, pour la raison ci-dessus.
> 3. Pour les lieux publics (mairies, écoles, bibliothèques), Sirene donne le
>    SIRET de la collectivité : utile pour le lien, mais il ne désigne pas
>    l'établissement lui-même.
>
> Nous pouvons préparer le rapprochement en masse et vous le livrer sous forme de
> suggestions (id d'ERP, SIRET proposé, preuve, score), à charge pour vous de
> valider — nous ne demandons aucun accès en écriture.

---

## 3. Ce que nous ne demandons pas

- Aucun accès à leur base, aucun PATCH, aucun compte.
- Aucune modification de leur modèle de données : les deux propositions tiennent
  dans un champ (`duplicate_of`) et dans une règle de saisie (SIRET à la
  revendication).
- Aucune fusion de notre côté : nos paires restent des candidats, jamais des
  suppressions.

## 4. Chiffres de référence

| Mesure | Valeur |
|---|---|
| ERP dans l'export du 17/11/2026 | 635 173 |
| `rnb_id` renseigné | 56,3 % |
| `siret` renseigné | 1,0 % |
| Paires même bâtiment (nom proche) | 3 200 |
| Paires même adresse exacte, `rnb_id` incomplet | 2 434 |
| Paires sans preuve | 2 829 |
| Paires écartées (bâtiments différents prouvés) | 950 |
| ERP sur un même `rnb_id` (maximum) | 196 |
| SIRET retrouvés par nom + code postal (échantillon de 40) | 4 |
