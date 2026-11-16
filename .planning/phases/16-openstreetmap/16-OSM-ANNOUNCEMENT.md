# Phase 16 — publication OSM : les textes à poster

Trois textes, dans cet ordre. Le code est fini ; la publication est manuelle, et la gate de
`osm publish` refuse tant qu'un humain n'a pas fait les trois gestes de la fin de ce document.

Ce qui a changé après lecture du fil 14961 : nous citons Complète Tes Commerces et OSM Mon Commerce
au lieu de demander s'ils existent, et nous répondons à la question que pyrog avait posée en 2025
(« peut-on extraire des données pour enrichir OSM ? ») par du code plutôt que par un avis.

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

## 2. Contribution — catégorie « Contribuer »

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

**Après avoir posté :** répondre aussi dans le fil
[Acceslibre et utilisation détournée des données OSM](https://forum.openstreetmap.fr/t/acceslibre-et-utilisation-detourne-des-donnees-osm/14961)
avec deux phrases et un lien vers le nouveau fil. Ce fil-ci contient la plainte ; le nouveau contient
la réponse. Ne pas y développer l'argumentaire.

## 3. Wiki — https://wiki.openstreetmap.org/wiki/Import/LetMeGetIn

Contenu de `data/referential/osm/wiki_page.md`, **sans le bloc de frontmatter** `--- url: … ---`
(champ interne de la gate). La page est en anglais, comme le reste du wiki OSM.

---

## 4. Fermer la gate

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

## 5. Après la discussion

Le retour peut demander de retirer des catégories ou des tags. Les fichiers concernés sont
`data/referential/category_mapping.csv` (colonne `osm_tag`) et
`data/referential/osm_accessibility_tags.csv` ; `osm tags audit` vérifie qu'ils restent cohérents.
Rien de cela n'est dans le code : une réponse négative se traduit par une édition de données.
