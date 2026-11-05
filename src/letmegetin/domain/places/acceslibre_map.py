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
# The keys are the export's real column names (verified against acceslibre.csv,
# 2026-11-05, 101 columns). The previous keys ("acces_entree", ...) matched no
# column at all, so every accessibility value was silently dropped and
# `coverage.fill_rate` sat at 0 for 634 931 places.
FIELD_MAP: dict[str, str] = {
    "entree_pmr": "entree-acces",
    "entree_largeur_mini": "entree-largeur-de-porte-cm",
    "entree_marches": "entree-obstacles-a-la-porte-d-entree",
    "entree_porte_manoeuvre": "entree-ouverture-de-porte",
    "accueil_cheminement_plain_pied": "circulation-circulation-dans-les-allees",
    "sanitaires_presence": "services-et-equipements-sanitaires",
    "stationnement_ext_pmr": "exterieur-place-gig-gic-a-proximite",
    "transport_station_presence": "exterieur-transports-accessibles-a-proximite",
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
