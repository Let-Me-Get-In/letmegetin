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

### Overture taxonomy — what it is
Overture classifies places with a **hierarchical taxonomy**: 13 top-level (L0) → ~2,100 leaf
categories → ~280 **basic categories**.
- `basic_category` — a "cognitively basic" label (e.g. `casual_eatery`).
- `taxonomy.hierarchy` — the full path, e.g. `[food_and_drink, restaurant, casual_eatery, gas_station_sushi]`.
- `taxonomy.primary` — the most specific label.
- `taxonomy.alternate` — other labels.
Aggregation traverses `hierarchy` (all restaurants = any path containing `restaurant`).

### Comparison with our 158 categories
| Our category | Overture `basic_category` | Overture `taxonomy.hierarchy` |
|---|---|---|
| hotel | hotel | [lodging, hotel] |
| restaurant | restaurant | [food_and_drink, restaurant] |
| bakery | bakery | [food_and_drink, bakery] |
| pharmacy | pharmacy | [health_and_medical, pharmacy] |
| museum | museum | [arts_and_entertainment, museum] |
| gite (FR) | vacation_rental | [lodging, vacation_rental] |
| bazar | variety_store | [shopping, variety_store] |
| antique_furniture_store | antique_furniture_store | [shopping, antique_furniture_store] |

**Decision:** adopt Overture's **`basic_category`** (~280) as the public category list; keep our
158 as `legacy_category` / alias, mapped in `category_mapping`.

### Persistence
- `data/referential/category_mapping.csv` — one row per category:
  `slug;name;overture_category;osm_tag;acceslibre_family;notes`
- Table `category_mapping` resolves a category to Overture/OSM/Acceslibre and maps source
  records to a category.
- Priority when importing: **Overture `basic_category`** → `osm_tag` → Acceslibre family.

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

## 7. Decisions (resolved with the product owner, 2026-10-27)

- **Categories**: adopt the Overture `basic_category` as the public taxonomy; keep the 158
  Jaccede categories as `legacy_category` aliases.
- **Groups**: expose **our 7 groups** (form-friendly) with an `en17210_ref` per criterion
  (traceability to EN 17210 / T&H).
- **Handicap families**: model **4 first-class families** — `moteur`, `auditif`, `visuel`,
  `mental` (cognitive) — instead of the motor-only Jaccede grid.
  - `Criterion.handicap_families: list[HandicapFamily]`
  - `AccessibilityFilter.handicap_families`
  - `Place.accessibility_by_family` (computed score per family)
  - API: `?family=` on the grid and search; criteria expose `handicap_families`.
  - Admin: set the families per criterion.
  - Add non-motor criteria (induction loop, sign language, braille, contrast, audio description,
    easy-read, quiet space, tactile paving…) from the 182 library + T&H/EN 17210.
- **Why**: Jaccede was essentially motor-only; hearing, visual and cognitive accessibility was
  under-represented. The 4 families are a first-class product feature.

---

*Created: 2026-10-27. See `03-CONTEXT.md` for the dedup/serving/licensing decisions.*
