# Phase 16 — publication OSM : les textes à poster

Trois textes, dans cet ordre. Le code est fini ; la publication est manuelle, et la gate de
`osm publish` refuse tant qu'un humain n'a pas fait les trois gestes de la fin de ce document.

Ce qui a changé depuis la première version : la Licence Ouverte 2.0 est lue dans le texte, et elle
tranche la question de licence au lieu de la laisser en suspens. Les deux messages en tiennent compte,
et la page wiki gagne une section sur les licences.

Le détail utile, pour savoir ce qu'on affirme :

- LO 2.0 autorise à « diffuser, redistribuer, publier et transmettre », y compris « en la combinant
  avec d'autres informations », à une seule condition : la paternité (source et date de mise à jour).
- LO 2.0 « a été conçue pour être compatible avec toute licence libre qui exige a minima la mention de
  paternité ».
- Conséquence : LO vers ODbL passe, parce qu'une obligation d'attribution satisfait une obligation
  d'attribution plus partage à l'identique. L'inverse ne passe pas : une ligne ODbL imposerait le
  partage à l'identique à une base publiée en LO.

---

## 1. Présentation — catégorie « Présentation »

```
Bonjour,

Je m'appelle Sébastien Billion et j'ai passé cinq ans sur Jaccede, la plateforme
d'accessibilité qui a fermé en décembre 2024.

J'y ai fait la refonte et la migration AWS, l'API REST v3 puis v4 en Flask, le
référentiel de catégories et de critères, et la déduplication des lieux. Après mon
départ, les sauvegardes ont été supprimées et personne n'a pu exporter la donnée.
Un référentiel construit sur des années a disparu comme ça.

Depuis, je le reconstruis : LetMeGetIn, 158 catégories, 182 critères, 52 filtres,
quatre familles de handicap, en FastAPI et PostgreSQL/PostGIS, alimenté par les
634 931 établissements de l'open data AccesLibre. Le code est sous AGPL et public,
l'API est en lecture seule.

https://letmegetin.org

Je viens ici pour une raison précise. Je lis OSM et je veux rendre ce que mes
contributeurs enregistrent, sous forme de tags d'accessibilité, dans de petits
changesets revus à la main. La proposition est sur le wiki (Import/LetMeGetIn) et
j'ouvre un fil dans Contribuer.

Je précise ce que je ne demande pas : aucun mandat au-delà de la France. La page
parle de l'ambition européenne, mais chaque pays aurait sa propre proposition et
sa propre discussion, avec sa communauté.

Et la limite, autant la dire avant qu'on me la trouve : le projet n'a pas encore
de communauté. Il a une structure et de la couverture, pas de contributeurs.
C'est pour ça que je commence par demander l'avis de ceux qui savent plutôt que
par publier.
```

## 2. Contribution — Contribuer > Projets de contribution

Objet : `Proposition — retour d'accessibilité LetMeGetIn vers OSM (petits changesets, sans import)`

```
Bonjour,

Je développe LetMeGetIn (https://letmegetin.org), la réécriture moderne de
Jaccede : un référentiel d'accessibilité normalisé, en API publique et sous licence
ouverte. Je viens vous présenter une proposition en deux temps, et surtout pas un
import de données vers OSM : je ne veux rien ajouter à la base, seulement lire et,
plus tard, rendre.

Ce que je lis. L'extrait Geofabrik France, en streaming. Tous les POI des
catégories que j'ai explicitement mappées : 124 de mes 158 catégories ont un tag
OSM revu. Le but est de faire apparaître les lieux pas encore documentés en
accessibilité. Une boulangerie sans wheelchair est précisément le lieu qu'un
contributeur peut compléter chez moi, mais seulement s'il est visible.

Ce que je propose de rendre. Les réponses d'accessibilité que mes contributeurs
enregistrent pour ces lieux, sous forme de tags OSM, dans de petits changesets
revus à la main. Le générateur ré-émet le jeu complet de tags de l'objet, parce
qu'un modify remplace tout ; un objet dont je ne détiens pas la version et les
tags bruts n'est jamais émis. Rien n'est créé, rien n'est supprimé, et une valeur
d'OSM plus récente que la mienne gagne toujours : je saute et je journalise.

Je n'ai mappé que ce que je peux justifier. wheelchair=no, ramp, handrail et
hearing_loop ne sont pas mappés aujourd'hui, parce que mon référentiel n'a pas de
critère qui puisse les porter sans inventer du sens. Un couple clé=valeur non revu
est ignoré et compté, et je publie la liste des combinaisons non mappées les plus
fréquentes pour que le mapping grandisse par la preuve.

Sur les licences, puisqu'une partie de mes données vient d'ailleurs. Ma source
principale, AccesLibre, publie sous Licence Ouverte 2.0. Cette licence autorise
explicitement à redistribuer et à combiner avec d'autres informations, à une seule
condition : la paternité, c'est-à-dire la source et la date de dernière mise à
jour. Elle précise aussi qu'elle est compatible avec toute licence libre exigeant
au minimum la mention de paternité. Donc leurs données peuvent entrer dans une
base ODbL et remonter vers OSM, et c'est ce que je fais ; l'attribution vit dans
cette page wiki et dans les tags de changeset, pas dans chaque objet.

Dans l'autre sens, je ne peux pas. Une ligne dérivée d'OSM est sous ODbL, donc à
partage à l'identique ; l'envoyer à une base publiée en Licence Ouverte lui
imposerait une obligation qu'elle ne peut pas porter. C'est pour ça que je ne
pousse jamais de donnée OSM vers cette source, et c'est encodé comme une règle de
données, pas comme un commentaire dans le code.

Sur ce qui existe déjà. Je ne prétends pas être le premier. Complète Tes Commerces
aide déjà à compléter les commerces d'une ville dans OSM, wheelchair compris, avec
un tableau de bord par ville. OSM Mon Commerce fait la même chose côté boutiques.
Ces outils répondent à « qu'est-ce qui manque ». Mon référentiel répond à « à quoi
ressemble ce lieu, pour chaque handicap » : 158 catégories, 182 critères, quatre
familles. Je lis OSM et je rends, donc les deux devraient se renforcer. Si un
mapping ou un workflow existe déjà et que je devrais l'adopter plutôt que d'en
inventer un troisième, dites-le moi.

Et la suite, pour être franc. LetMeGetIn couvre la France aujourd'hui. L'ambition,
si le projet tient ses promesses (assez de lieux documentés, assez de
contributeurs, une relation de travail avec la communauté OSM française), est
d'ouvrir le référentiel au reste de l'Europe, puis au-delà.

Cette proposition ne concerne que la France. Je lis l'extrait français et j'écris
sur des objets français ; je ne demande ni n'implique aucun accord pour un import
ailleurs. Chaque pays a ses conventions de tag, sa communauté et ses règles
d'import : un élargissement viendrait avec sa propre proposition et sa propre
discussion, pays par pays.

Rien n'est encore envoyé. Le dépôt génère un fichier osmChange qu'un opérateur
ouvre dans JOSM et envoie après revue ; le code refuse de générer quoi que ce soit
sans consentement explicite aux contributor terms. Le code est public :
https://github.com/Let-Me-Get-In/letmegetin

La proposition complète est sur le wiki :
https://wiki.openstreetmap.org/wiki/Import/LetMeGetIn

Mes questions :

1. Le mapping de catégories vous paraît-il raisonnable, ou y a-t-il des tags que
   vous refuseriez ?
2. Pour un retour d'accessibilité, préférez-vous des changesets source=survey
   uniquement, ou acceptez-vous aussi des réponses déclaratives si elles sont
   marquées comme telles ?
3. Comment articuler ça avec Complète Tes Commerces et OSM Mon Commerce ? S'il y a
   un mapping ou un workflow à rejoindre, je préfère l'adopter que créer un
   troisième outil.
4. Sur la portée : si le projet couvre un jour d'autres pays, préférez-vous un
   aller-retour par pays, coordonné avec chaque communauté locale, ou autre chose ?

Merci d'avance. Et si la réponse est « pas maintenant », je préfère le savoir avant
d'écrire une ligne dans OSM.
```

## 3. Réponse dans le fil « Acceslibre et utilisation détournée des données OSM »

Fil : https://forum.openstreetmap.fr/t/acceslibre-et-utilisation-detourne-des-donnees-osm/14961

À poster **après** le fil principal, et à garder court. Ce fil a trois ans ; y arriver avec un
argumentaire complet se lira comme une relance. Deux paragraphes et un lien suffisent.

```
Bonjour,

Je tombe sur ce fil en travaillant sur un problème voisin, et je crois pouvoir
répondre à la question posée au départ, au moins pour la partie licence.

La Licence Ouverte 2.0, sous laquelle AccesLibre publie, autorise explicitement à
redistribuer et à combiner avec d'autres informations, à une seule condition : la
paternité. Elle précise aussi qu'elle est compatible avec toute licence libre
exigeant au minimum la mention de paternité. Donc leurs données peuvent aller vers
OSM : une obligation d'attribution satisfait l'attribution exigée par l'ODbL.
L'inverse ne marche pas, et c'est là que la base dérivée se referme : une ligne
dérivée d'OSM est en partage à l'identique, l'envoyer chez eux leur imposerait une
obligation que leur licence ne peut pas porter.

C'est la lecture que j'applique dans le projet sur lequel je travaille
(https://letmegetin.org) : je lis OSM, je rends les réponses d'accessibilité de mes
contributeurs en petits changesets revus à la main, et je ne pousse jamais une
ligne dérivée d'OSM vers une base en Licence Ouverte. La proposition complète, avec
ce qu'on lit, ce qu'on écrit et ce qu'on refuse d'écrire, est ici :
https://forum.openstreetmap.fr/t/...

Je ne prétends pas que ça règle leur cas. Mais si quelqu'un veut savoir à quoi
ressemble un aller-retour qui respecte les deux licences, le code est public et
c'est fait pour être critiqué.
```

**Ne pas** écrire dans ce fil que la réponse d'AccesLibre autorise quoi que ce soit. Leur licence
autorise, indépendamment d'eux ; l'accord oral ne fait que confirmer. Écrire l'inverse leur ferait
endosser une décision qu'ils n'ont pas à prendre, dans un fil qui leur reproche déjà leur silence.

## 4. Wiki — https://wiki.openstreetmap.org/wiki/Import/LetMeGetIn

Contenu de `data/referential/osm/wiki_page.md`, **sans le bloc de frontmatter** `--- url: … ---`
(champ interne de la gate), et sous forme **wikitext** : `data/referential/osm/wiki_page.wikitext`.
La page est en anglais, comme le reste du wiki OSM.

Résumé d'édition : `Create the LetMeGetIn accessibility round-trip proposal: Geofabrik France extract
read in streaming, accessibility answers written back as reviewed small changesets`

---

## 5. Fermer la gate

```bash
# 1. URL réelle du wiki dans la page elle-même
#    remplacer `url: <to be published>` par `url: https://wiki.openstreetmap.org/wiki/Import/LetMeGetIn`
# 2. URL du fil de discussion
echo -n "https://forum.openstreetmap.fr/t/..." > data/referential/osm/discussion_url.txt
# 3. Consentement aux contributor terms (à lire avant)
echo "accepted" > data/referential/osm/tos_consent.txt
```

Puis :

```bash
uv run python -m letmegetin.admin osm publish --out /tmp/osm-review
```

`answers.osmChange` et `changeset_comment.txt` apparaissent dans `/tmp/osm-review`, avec le vrai lien
wiki dans le commentaire. C'est ce fichier qu'on ouvre dans JOSM, en un premier changeset de quelques
dizaines d'objets.

## 6. Après la discussion

Le retour peut demander de retirer des catégories ou des tags. Les fichiers concernés sont
`data/referential/category_mapping.csv` (colonne `osm_tag`) et
`data/referential/osm_accessibility_tags.csv` ; `osm tags audit` vérifie qu'ils restent cohérents.
Rien de cela n'est dans le code : une réponse négative se traduit par une édition de données.
