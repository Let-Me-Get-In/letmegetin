# Phase 16 — publication OSM : ce qui reste à faire à la main

Le code est fini. La gate de `osm publish` refuse tant que trois choses ne sont pas faites par un
humain, dans cet ordre.

## 1. Publier la page wiki

Créer la page **https://wiki.openstreetmap.org/wiki/Import/LetMeGetIn** avec le contenu de
`data/referential/osm/wiki_page.md` (retirer le bloc de frontmatter `--- url: … ---`, c'est un champ
interne).

Le titre `Import/LetMeGetIn` suit la convention des autres propositions d'import.
La page suit le squelette `Import/Plan Outline` : objectifs, calendrier, données, préparation,
fusion, QA, discussion.

## 2. Ouvrir la discussion

Poster sur **https://forum.openstreetmap.fr/** (catégorie *Import*) et, si tu veux couvrir la liste,
sur **talk-fr** (https://lists.openstreetmap.org/listinfo/talk-fr).

Texte prêt à poster :

---

**Objet : Proposition — retour d'accessibilité LetMeGetIn vers OSM (petits changesets, sans import)**

Bonjour,

Je m'appelle Sébastien Billion, je développe **LetMeGetIn** (https://letmegetin.org), la réécriture
moderne de Jaccede : un référentiel d'accessibilité normalisé, en API publique et sous licence
ouverte.

Je viens vous présenter une proposition en deux temps, et surtout **pas un import de données vers
OSM** : je ne veux rien ajouter à la base, seulement lire et, plus tard, rendre.

**Ce que je lis.** L'extrait Geofabrik France, en streaming. Tous les POI des catégories que j'ai
explicitement mappées (124 de mes 158 catégories ont un tag OSM revu). Le but est de faire apparaître
les lieux **pas encore documentés** en accessibilité : une boulangerie sans `wheelchair` est
précisément le lieu qu'un contributeur peut compléter chez moi, mais seulement s'il est visible.

**Ce que je propose de rendre.** Les réponses d'accessibilité que mes contributeurs enregistrent pour
ces lieux, sous forme de tags OSM, dans de **petits changesets revus à la main**. Le générateur
ré-émet le jeu complet de tags de l'objet (un `<modify>` remplace tout) ; un objet dont je ne
détiens pas la version et les tags bruts n'est jamais émis. Rien n'est créé, rien n'est supprimé, et
**une valeur d'OSM plus récente que la mienne gagne toujours** — je saute et je journalise.

Je n'ai mappé que ce que je peux justifier : `wheelchair=no`, `ramp`, `handrail` et `hearing_loop` ne
sont **pas** mappés aujourd'hui, parce que mon référentiel n'a pas de critère qui puisse les porter
sans inventer du sens. Un couple `clé=valeur` non revu est ignoré et compté, et je publie la liste
des combinaisons non mappées les plus fréquentes pour que le mapping grandisse par la preuve.

**Rien n'est encore envoyé.** Le dépôt génère un fichier `.osmChange` qu'un opérateur ouvre dans JOSM
et envoie après revue ; le code refuse de générer quoi que ce soit sans consentement explicite aux
contributor terms. Le code est public :
https://github.com/Let-Me-Get-In/letmegetin

La proposition complète est sur le wiki :
**https://wiki.openstreetmap.org/wiki/Import/LetMeGetIn**

**Mes questions :**
1. Le mapping de catégories vous paraît-il raisonnable, ou y a-t-il des tags que vous refuseriez ?
2. Pour un retour d'accessibilité, préférez-vous des changesets `source=survey` uniquement, ou
   acceptez-vous aussi des réponses déclaratives (non vérifiées sur le terrain) si elles sont
   marquées comme telles ?
3. Y a-t-il un projet existant en France que je devrais rejoindre plutôt que de faire ça de mon côté ?

Merci d'avance — et si la réponse est « pas maintenant », je préfère le savoir avant d'écrire une
ligne dans OSM.

---

## 3. Fermer la gate

Une fois les deux URL réelles en main :

```bash
# 1. URL du wiki dans la page elle-même
#    remplacer `url: <to be published>` par `url: https://wiki.openstreetmap.org/wiki/Import/LetMeGetIn`
# 2. URL du fil de discussion
echo -n "https://forum.openstreetmap.fr/t/..." > data/referential/osm/discussion_url.txt
# 3. Consentement aux contributor terms (lis-les d'abord)
echo "accepted" > data/referential/osm/tos_consent.txt
```

Puis `osm publish` doit passer :

```bash
uv run python -m letmegetin.admin osm publish --out /tmp/osm-review
```

`answers.osmChange` et `changeset_comment.txt` apparaissent dans `/tmp/osm-review`, avec le vrai lien
wiki dans le commentaire. C'est ce fichier qu'on ouvre dans JOSM.

## 4. Après la discussion

Le retour de la communauté peut demander de retirer des catégories ou des tags du mapping. Les deux
fichiers concernés sont `data/referential/category_mapping.csv` (colonne `osm_tag`) et
`data/referential/osm_accessibility_tags.csv` ; `osm tags audit` vérifie qu'ils restent cohérents.
Rien de tout cela n'est dans le code, donc une réponse négative se traduit par une édition de données.
