"""Map Acceslibre accessibility columns onto our criterion slugs.

Acceslibre's export is much broader than the 19 base criteria: only one-to-one fields are kept,
and anything unknown is ignored rather than guessed. The raw value and its source key travel with
the value, so a consumer can always trace a claim back to the source column.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SOURCE = "acceslibre"

# One source column per criterion: where Acceslibre splits a criterion into several columns
# (plain-pied/rampe/marches), the importer keeps the coarse field and leaves the detail out.
FIELD_MAP: dict[str, str] = {
    "acces_entree": "entree-acces",
    "acces_entree_largeur": "entree-largeur-de-porte-cm",
    "acces_entree_marches": "entree-obstacles-a-la-porte-d-entree",
    "acces_entree_automatique": "entree-ouverture-de-porte",
    "acces_cheminement": "circulation-circulation-dans-les-allees",
    "acces_toilettes": "services-et-equipements-sanitaires",
    "acces_stationnement": "exterieur-place-gig-gic-a-proximite",
    "acces_transport": "exterieur-transports-accessibles-a-proximite",
}

_EMPTY = (None, "")


def accessibility_values(record: Mapping[str, Any]) -> dict[str, dict[str, object]]:
    """Return ``{criterion_slug: value}`` for the mapped columns present in the record."""
    values: dict[str, dict[str, object]] = {}
    for key, slug in FIELD_MAP.items():
        raw = record.get(key)
        if raw in _EMPTY:
            continue
        values[slug] = {"value": raw, "source": SOURCE, "key": key}
    return values
