# Doublons dans les données AccesLibre — mesures sur un import complet

Document destiné à l'équipe AccesLibre. Écrit en français pour cette raison ; le
reste de la documentation technique du dépôt est en anglais.

## Conditions de mesure

- Source : `acceslibre.csv`, publié sur data.gouv le **17 novembre 2026 à 00 h 05**
  (205 Mo), soit 635 173 ERP.
- Import complet dans une base vide, sans aucun dédoublonnage préalable, pour
  mesurer la donnée telle qu'elle est publiée.
- Les croisements utilisent les champs `rnb_id`, `siret`, `numero`, `voie`,
  `commune` et `activite` du fichier source.
- Notre dédoublonnage a ensuite tourné sur cette base intacte, afin de comparer ce
  qu'il trouve à ce que la donnée contient réellement.

## 1. Complétude des champs utiles au rapprochement

| Champ | Renseigné | Remarque |
|---|---|---|
| `latitude` / `longitude` | 100 % | |
| `voie` | 98,8 % | |
| `commune` | 100 % | |
| `numero` | 80,2 % | |
| `code_insee` | 86,8 % | |
| `rnb_id` | **56,3 %** | identifiant bâtiment du Référentiel national des bâtiments |
| `site_internet` | 49,3 % | |
| `siret` | **1,0 %** | |
| `contact_url` | 3,1 % | |

Deux champs méritent d'être soulignés : `rnb_id` est présent sur plus d'un ERP sur
deux, et `siret` sur un sur cent.

## 2. Combien de doublons

Mesuré par deux règles indépendantes, qui ne s'appuient pas sur la distance :

| Règle | Principe | Lignes en trop | Taux |
|---|---|---|---|
| A | même `rnb_id` + même nom normalisé + même `activite` | 950 | 0,15 % |
| B | même nom normalisé + même numéro + même voie + même commune | 2 845 | 0,45 % |
| A ∪ B | | **5 526** | **0,87 %** |

Par département, sur l'union : Paris (75) 482, Rhône (69) 411, Marne (51) 321,
Loire-Atlantique (44) 144, Hauts-de-Seine (92) 143, Gironde (33) 125.

Le fichier contient 391 valeurs d'`activite` distinctes, dont « Mairie » (38 009
ERP), « Restauration rapide » (37 046), « Coiffure » (31 293) et « Restaurant »
(25 251).

**Conclusion : moins de 1 % de la base est dupliquée.** Le problème n'est donc pas
massif — mais il est concentré, et il est détectable de façon fiable quand les bons
champs sont utilisés.

## 3. Pourquoi une déduplication par la distance ne fonctionne pas

C'est le résultat le plus utile de ces mesures, et il est dirimant.

| Mesure | Valeur |
|---|---|
| Paires d'ERP à moins de 50 m | **6 665 090** |
| Paires signalées par notre méthode nom + distance | 12 359 |
| dont même bâtiment (`rnb_id` identique) | 3 785 (30,6 %) |
| dont bâtiments **différents** alors que les deux `rnb_id` sont renseignés | 1 782 (14,4 %) |
| dont `rnb_id` absent d'un côté au moins | 6 792 (55,0 %) |
| dont même adresse (numéro + voie + commune) | 7 045 (57,0 %) |
| dont même commune mais adresse différente | 5 159 (41,7 %) |
| dont communes différentes | 155 (1,3 %) |

Une déduplication par rayon produit **6,6 millions de paires** pour quelques
milliers de doublons réels. C'est mécanique : le modèle est « un ERP = un
établissement », donc un lycée, une mairie, un hôpital ou un centre commercial
portent légitimement plusieurs ERP au même point. Le maximum observé sur un même
`rnb_id` est de **196 ERP** — un campus ou un hôpital.

Et surtout : parmi les paires où le bâtiment est connu des deux côtés, **32 % sont
dans deux bâtiments différents**. La proximité géographique n'est pas seulement
insuffisante, elle trompe.

## 4. La méthode que nous appliquons, et ce qu'elle vaut

1. Normalisation du nom : minuscules, accents retirés, abréviations développées,
   ponctuation réduite. Le nom de la commune est retiré en fin de nom, sinon deux
   commerces voisins se ressemblent par leur seule ville.
2. Similarité par `difflib` de la bibliothèque standard, sans modèle ni service
   externe.
3. Recherche des voisins dans une grille de 50 m en mémoire : 6,7 millions de
   paires comparées en 1 min 35 sur la base complète, contre quatre heures pour une
   requête spatiale par ligne.
4. Seuils : liaison automatique au-delà de 0,90, revue humaine entre 0,75 et 0,90.
   Le plancher a été monté de 0,60 à 0,75 après mesure : 18 987 des 35 901 paires
   de la file nationale tombaient entre 0,60 et 0,70 et n'étaient que du vocabulaire
   de métier partagé (« ZOZAN KEBAB » contre « Antalya Kebab »).
5. Aucune suppression : une liaison écrit une référence vers le canonique, une
   fusion est une décision humaine journalisée avec son auteur et son score.

**Ce que cette méthode ne sait pas faire, et c'était notre propre limite :** elle
ignorait `rnb_id`, `siret`, `numero` et `voie`, que nous n'ingérions pas. Nous les
ingérons désormais : l'adresse est reconstruite à partir de `numero` + `voie`
(98,8 % des fiches ont une voie, 80,2 % un numéro), et deux `rnb_id` connus et
différents constituent désormais un *veto* : deux bâtiments distincts ne sont
jamais signalés comme doublons, quel que soit le score de nom. Le tableau de la
section 3 montre ce que l'ancienne méthode coûtait : sur 12 359 paires signalées,
14 % étaient démontrablement fausses et 55 % ne pouvaient pas être tranchées faute
d'identifiant de bâtiment.

## 5. Ce que nous proposons

Dans l'ordre de valeur :

1. **Utiliser `rnb_id` comme signal principal, jamais comme clé d'ERP.** Deux
   fiches du même ERP partagent le même bâtiment ; deux ERP différents d'un même
   bâtiment sont un cas légitime et fréquent — nous avons mesuré jusqu'à 196 ERP
   sur un même `rnb_id`. La règle « même bâtiment + même nom normalisé » sépare
   les deux sans ambiguïté. C'est la règle A ci-dessus, et elle donne le taux le
   plus fiable. En revanche `rnb_id` ne peut pas identifier un ERP, et il ne peut
   pas davantage servir de clé stable côté OSM : le RNB **désactive** les
   identifiants des bâtiments fusionnés (voir section 7).
2. **Augmenter la couverture de `rnb_id`.** À 56 %, la moitié de la base reste
   indécidable. C'est, de loin, le meilleur investissement qualité disponible : il
   ne demande aucun traitement de texte, seulement un rapprochement avec le
   référentiel national des bâtiments, qui est ouvert.
3. **Renseigner `siret` plus souvent.** À 1 %, le champ est inutilisable pour le
   rapprochement. Il ne concerne sans doute qu'une partie des ERP (les équipements
   publics n'en ont pas), mais si la valeur est disponible en interne, elle vaut
   d'être publiée.
4. **Publier un indicateur de doublon plutôt que fusionner.** Un champ
   « probablement le même établissement que X », avec la règle et le score, laisse
   la décision à l'opérateur et rend l'erreur réversible. Dans les 12 359 paires
   signalées, 3 118 apportaient une information absente de l'original (site web) :
   un doublon n'est pas forcément un déchet, c'est parfois une occasion de fusion
   avec gain.
5. **Normaliser `activite`.** 391 valeurs libres pour un référentiel d'activités
   fermé serait plus exploitable, y compris pour nous : notre classement en
   158 catégories dépend de ces libellés.

## 6. Ce que ces chiffres ne disent pas

- « Même bâtiment » n'est pas « doublon » : un hôpital héberge des ERP distincts.
  La règle A ajoute le nom et l'activité pour cette raison, mais elle reste un
  signal, pas une preuve.
- La règle B rate les doublons saisis avec deux graphies d'adresse différentes
  (« 12 rue » contre « 12 rue » avec un type de voie développé), et sur-compte
  les chaînes qui ont deux points de vente dans la même commune.
- Les 155 paires de communes différentes signalées par notre méthode sont des
  faux positifs, sauf erreur de saisie de commune d'un côté.
- Les chiffres portent sur le fichier du 17 novembre 2026. La base bouge : elle
  comptait 634 931 ERP lors de notre import précédent, soit 242 de moins.

## 7. Deux questions tranchées dans leur code source et dans la documentation du RNB

Nous avons lu le code d'AccesLibre (`MTES-MCT/acceslibre`, relevé du 17 novembre
2026) et la FAQ du Référentiel national des bâtiments, parce que les deux
réponses changent ce qu'on peut demander.

**Le `rnb_id` est pérenne, mais il peut être désactivé.** Le RNB garantit qu'un
identifiant attribué à un bâtiment ne change plus, et qu'il n'est jamais réutilisé.
En revanche, quand deux bâtiments fusionnent, « les ID-RNB existants sont
désactivés » : un nouveau bâtiment est créé et le lien avec les anciens est
conservé côté RNB. Un `rnb_id` lu dans un export peut donc désigner un bâtiment
qui n'existe plus comme tel. Il faut le traiter comme un lien vers un bâtiment à
une date, pas comme une vérité permanente.

**AccesLibre ne conserve qu'un seul `rnb_id` par ERP.** La table des sources
externes a une contrainte d'unicité `(source, erp)` ; leur import RNB le dit
explicitement — « we cannot insert more than 1 source_id per source … We will
manage only the first RNB_id here » — et il supprime l'ancienne ligne avant
d'écrire la première de la nouvelle liste. Un ERP qui occupe plusieurs bâtiments
garde donc un identifiant arbitraire, et cet identifiant peut changer d'un import
RNB à l'autre.

**Il n'existe aucun indicateur de doublon, et c'est volontaire.** Leurs doublons
sont traités côté serveur : `remove_duplicates` rapproche les fiches d'une même
commune dont le nom est identique et qui sont à moins de 75 m, fusionne les
réponses champ par champ en préférant la source humaine, puis **supprime** la
fiche en trop. L'export ne contient que les ERP publiés. Autrement dit, l'export
que nous recevons est *déjà après nettoyage* : les quelque 5 500 doublons que
nous mesurons sont précisément ceux que leur règle a ratés, et rien dans le
fichier ne permet de savoir qu'une fiche en a absorbé une autre. C'est pourquoi
nous demandons un indicateur plutôt qu'une fusion : une fiche supprimée ne laisse
aucune trace pour ceux qui, comme nous, réutilisent l'export.
