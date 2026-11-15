Objet : Demande de clé API — LetMeGetIn (réutilisation d'Acceslibre et retour de contributions)

Bonjour,

Je m'appelle Sébastien Billion, je développe LetMeGetIn (https://letmegetin.org), un service
public et open source qui reprend l'idée de Jaccede : un référentiel d'accessibilité normalisé,
exposé en API publique, que n'importe quel site peut consommer.

Nous avons déjà importé votre jeu de données national (634 931 établissements au 6 novembre 2026,
via l'export Etalab 2.0), avec attribution, et nous le citons comme source dans notre export ouvert.

Nous souhaiterions maintenant faire le chemin inverse, et c'est l'objet de cette demande :

1. **Récupérer une clé API** pour interroger `GET /api/erps/` et vérifier la fraîcheur de nos
   lignes par rapport aux vôtres (aujourd'hui nous ne savons pas si un établissement a été modifié
   chez vous depuis notre import).

2. **Vous renvoyer nos contributions** via `PATCH /api/erps/<slug>/` et, si vous le souhaitez,
   `POST /api/erps/`. Nous n'enverrons que des lignes que nous détenons : nos contributions
   d'utilisateurs et vos propres données enrichies. **Jamais de ligne dérivée d'OpenStreetMap** —
   l'ODbL n'est pas compatible avec votre diffusion en Licence Ouverte, et nous ne voulons pas
   vous imposer une contamination de licence. Ce filtre est déjà implémenté de notre côté.

3. **Une autorisation écrite d'attribution.** Votre licence est l'Etalab 2.0, qui exige
   l'attribution. La nôtre est l'ODbL, qui exige une attribution cumulative. La page
   contributeurs d'OpenStreetMap ne permet pas de vous citer avec votre licence, ce qui nous
   empêche de pousser nos données vers OSM tant que nous ne pouvons pas vous créditer
   correctement. Si vous acceptez une mention du type « Données Acceslibre — Licence Ouverte
   2.0 » sur cette page, cela débloque ce flux.

4. **Votre attente en retour.** Je comprends que l'accès à votre API puisse être lié à une
   contrepartie. Dites-moi ce qui vous serait utile : un flux régulier de nos contributions,
   davantage de lieux complets sur votre plateforme, un retour d'expérience sur votre schéma,
   ou autre chose. Notre code est public et notre référentiel aussi ; nous n'avons rien à vendre
   et nous préférons poser la relation sur des termes clairs.

Un point technique qui peut vous intéresser : nous avons mesuré que seuls 8 de vos critères
portent des valeurs sur l'ensemble du jeu national, et que 4 champs sur 61 sont réellement
renseignés. Si un retour là-dessus vous est utile, je peux vous envoyer les chiffres détaillés.

Merci d'avance, et bravo pour ce que vous avez construit — c'est la référence en France, et
c'est précisément pour cela que nous construisons par-dessus plutôt qu'à côté.

Bien à vous,
Sébastien Billion
contact@letmegetin.org
https://letmegetin.org
