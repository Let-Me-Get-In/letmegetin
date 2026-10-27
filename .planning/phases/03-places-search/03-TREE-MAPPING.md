# Phase 3 — Accessibility Tree: Ontology & Mapping

**Purpose:** define the canonical criteria tree (ontology), map the existing Jaccede
categories/criteria onto it, and describe how the per-category grid is produced and served.

## 1. Target ontology (7 groups)

Aligned with **EN 17210 / ISO 21542** and the **Tourisme & Handicap** common trunk, and
compatible with the **OSM accessibility tags**.

| # | Group (fr) | EN 17210 / T&H sequence | OSM keys |
|---|---|---|---|
| 1 | Signalisation & cheminements | Signalisation & cheminements & éclairage | `traffic_sign`, `lit`, `highway=crossing`, `tactile_paving`, `parking_space:width`, `capacity:disabled` |
| 2 | Entrée & accès | Accès et portes | `entrance`, `entrance:step_count`, `entrance:width`, `entrance:door`, `entrance:automatic_door`, `ramp:wheelchair`, `wheelchair:turning_circle`, `kerb:height` |
| 3 | Circulation intérieure | Cheminements intérieurs, escaliers, ascenseurs | `wheelchair`, `highway=elevator` (`elevator:width`, `elevator:length`), `handrail`, `indoor`, `level` |
| 4 | Sanitaires | Sanitaires | `toilets:wheelchair` (+ `door_width`, `space_side`, `space_front`, `grab_rails`), `hand_basin:wheelchair`, `shower:wheelchair`, `changing_table` |
| 5 | Accueil, services & information | Accueil, services & information du public | `opening_hours`, `payment:*`, `staff_count`, `language:*`, `menu` (no OSM standard), `induction_loop` |
| 6 | Prévention & sécurité | Prévention — sécurité | `emergency:*`, `fire_alarm`, `evacuation` |
| 7 | Informations accessibilité | Informations accessibilité | `wheelchair:description`, `acceslibre`, `T&H` label, `website` |

**Rule:** every category grid = **standard core (groups 1-7)** `∩` category-specific
criteria. The base 19 criteria map as follows.

## 2. Existing 19 base criteria → ontology

| Current criterion | Group | OSM key(s) |
|---|---|---|
| Accès | 2 Entrée | `entrance`, `wheelchair` |
| Ouverture de porte | 2 Entrée | `entrance:door`, `entrance:automatic_door` |
| Largeur de porte (cm) | 2 Entrée | `entrance:width` |
| Obstacles à la porte d'entrée | 2 Entrée | `entrance:step_count`, `kerb:height` |
| L'entrée accessible est l'entrée principale | 2 Entrée | `entrance=main` |
| Circulation dans les allées | 3 Circulation | `wheelchair` |
| Accès en fauteuil à tout le lieu | 3 Circulation | `wheelchair` |
| Ascenseurs (dimensions) | 3 Circulation | `elevator:width`, `elevator:length` |
| Ascenseurs (adaptations) | 3 Circulation | `highway=elevator`, `tactile_paving` |
| Hauteur adaptée des comptoirs/guichets | 5 Accueil | — (no OSM standard) |
| Sanitaires | 4 Sanitaires | `toilets:wheelchair` |
| Personnel formé à l'accueil | 5 Accueil | — |
| Personnel initié à la langue des signes | 5 Accueil | — |
| Mobilier et équipements | 5 Accueil | — |
| Menu en braille | 5 Accueil | — |
| Trottoirs (obstacles) | 1 Signalisation | `kerb`, `tactile_paving` |
| Enseigne visible et lisible | 1 Signalisation | `traffic_sign` |
| Place GIG/GIC à proximité | 1 Signalisation | `parking_space=disabled`, `capacity:disabled` |
| Transports accessibles à proximité | 1 Signalisation | `public_transport=station`, `wheelchair` |

## 3. The 182-label vocabulary → aliases

The flat `criteria.json` is a **library** (Phase 2 `criterion_vocabulary`). Each label is
promoted into a standard criterion/option and kept as an `alias`:

```
vocabulary: "Accès de plain-pied"      -> criterion "Accès" / option "De plain-pied"
vocabulary: "Porte à ouverture manuelle" -> criterion "Ouverture de porte" / option "Manuelle"
vocabulary: "Ascenseur de grandes dimensions" -> criterion "Ascenseurs (dimensions)" / option "Grand"
```

Promotion is **manual** (admin Phase 2), because the labels mix groups, criteria and options.
Do not auto-insert the library into the tree.

## 4. Category mapping

- `data/referential/category_mapping.csv` — one row per category:
  `slug;name;overture_category;osm_tag;acceslibre_family;notes`
  (34 common categories pre-filled; the rest curated in the admin).
- Persist as a `category_mapping` table (Phase 2/3) so the API can resolve a category to
  Overture/OSM/Acceslibre, and imports can map a source record to a category.
- Priority when importing: **Overture `categories`** → `osm_tag` → Acceslibre family.

## 5. Serving the grid (performance)

- **Precompute** `category_grid(category_id, version, tree JSONB)` at seed/admin time.
- `GET /api/v1/categories/{slug}/grid` → precomputed tree, `ETag: W/"ref-<version>"`,
  `Cache-Control`, `304` on match.
- Optional `GET /api/v1/referential?version=` → all grids (gzip, CDN) for offline/mobile.
- A flat `GET /api/v1/criteria` (id, parent_id, position, type, label, description) for clients
  that build the tree themselves.
- Bump `referential_version` on any admin edit → clients refetch only when it changes.

## 6. Completion process

1. Curate `category_mapping.csv` (admin `category link-source`).
2. Promote the vocabulary library into the tree (admin `vocabulary promote`).
3. Set the standard core as `is_default` for all categories.
4. Add category-specific criteria overrides.
5. Regenerate the grids (`category_grid`) and bump `referential_version`.

## 7. Open questions (to settle with the product owner)

- Do we keep **all 158** Jaccede categories, or collapse them into the Overture taxonomy and
  keep the 158 as aliases? (Recommend: keep them as aliases, adopt the Overture taxonomy as the
  public category list.)
- Do we expose **EN 17210 sequences** verbatim, or our own 7 groups? (Recommend: our 7 groups,
  with an `en17210_ref` field for traceability.)
- Which **handicap families** (moteur/auditif/visuel/mental) are first-class on each criterion?
  (T&H uses 4 families; the Jaccede grid is motor-heavy — extend it.)

---

*Created: 2026-10-27. See `03-CONTEXT.md` for the dedup/serving/licensing decisions.*
