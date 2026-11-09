# LetMeGetIn — logo

Un repère de carte dont le contre-forme est une porte ouverte, seuil compris.
Deux lectures en un signe : le lieu (le repère) et l'accès (la porte). La porte
n'est pas fermée — pas de clé, pas de serrure : c'est une ouverture.

## Fichiers

| Fichier | Usage |
| --- | --- |
| `letmegetin-mark.svg` | Le symbole seul, `viewBox 0 0 64 64`, `currentColor`. Toute taille, toute couleur. |
| `letmegetin-app-icon.svg` | Icône d'app / favicon 512, tuile verte coins 112, symbole papier. |
| `letmegetin-logo.html` | Planche de contrôle : 16 à 128 px, lockup, trois fonds, icône. |
| `preview.png` | Capture de la planche. |

## Couleurs

Reprises telles quelles de l'interface (`web/src/app/globals.css`) :

- papier `#f7f4ec`, encre `#18211c`
- accent `#1f6f4a` (symbole sur papier)
- accent sombre `#7fd1a6` (symbole sur nuit `#101613`, ou sur `#17261d`)

Le symbole se pose en une seule couleur. Pas de dégradé, pas d'ombre, pas de contour.

## Lockup

Symbole à gauche, mot « LetMeGetIn » à droite, dans la police d'affichage de
l'interface (serif, `font-display`, graisse 600), « Me » en accent — la
composition déjà en place dans `SiteHeader`.

- écart symbole / mot : ≈ 0,3 × la hauteur du symbole
- hauteur du symbole ≈ 1,15 × la hauteur de capitale du mot
- deux tailles seulement : 34 px (en-tête, marketing) et 21 px (pied de page, dense)
- dans le texte, toujours le `text-accent` existant, jamais une autre teinte

## Règles

- Taille minimale du symbole seul : 16 px (l'icône d'onglet). En dessous, ne pas descendre.
- Zone de respiration : au moins ¼ de la largeur du symbole de chaque côté.
- Ne pas déformer, ne pas incliner, ne pas inverser la porte (bord arrondi en bas).
- Ne pas poser le symbole sur un vert proche de l'accent : garder un contraste de fond franc.
- Sur photo ou carte, utiliser le disque papier ou la tuile verte, jamais le symbole nu.

## Pas encore fait

Le logo n'est branché nulle part : `web/public/` n'a pas de favicon, et
`SiteHeader` n'affiche que le mot. Pour le poser : `web/src/app/icon.svg`
(contenu de `letmegetin-app-icon.svg`) et le SVG du symbole dans le lockup de
l'en-tête.
