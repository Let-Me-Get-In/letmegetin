"""Construit le seed du référentiel à partir des sources historiques.

Sources (dans data/referential/raw/) :
- category.csv, criterion.csv, filters.csv, th.csv  (Jaccede API v4, traductions IT)
- places_api_v3.rst                                 (doc API v3, grille complète catégorie 1)

Sortie (dans data/referential/) :
- categories.json, criteria.json, filters.json, th.json
- category_grids/category-1.json
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "referential" / "raw"
OUT = ROOT / "data" / "referential"


def slugify(value: str) -> str:
    """ASCII slug stable pour les libellés non latins ou accentués."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "item"


def read_csv(name: str) -> list[dict[str, str]]:
    with (RAW / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def build_categories() -> list[dict[str, object]]:
    seen: dict[str, dict[str, object]] = {}
    for row in read_csv("category.csv"):
        name = (row.get("Name") or "").strip()
        label_it = (row.get("Label It") or "").strip()
        if not name:
            continue
        entry = seen.setdefault(name, {"slug": name, "name": name, "label": {}})
        if label_it:
            entry["label"]["it"] = label_it  # type: ignore[index]
    return list(seen.values())


def build_criteria() -> list[dict[str, object]]:
    seen: dict[str, dict[str, object]] = {}
    for row in read_csv("criterion.csv"):
        label_fr = (row.get("Label Fr") or "").strip()
        label_it = (row.get("Label It") or "").strip()
        description_it = (row.get("Description It") or "").strip()
        if not label_fr and not label_it:
            continue
        slug = slugify(label_fr or label_it)
        entry = seen.setdefault(slug, {"slug": slug, "label": {}, "description": {}})
        if label_fr:
            entry["label"]["fr"] = label_fr  # type: ignore[index]
        if label_it:
            entry["label"]["it"] = label_it  # type: ignore[index]
        if description_it:
            entry["description"]["it"] = description_it  # type: ignore[index]
    return list(seen.values())


def build_filters() -> list[dict[str, object]]:
    return [
        {
            "slug": slugify(row.get("Label") or row.get("Label It") or ""),
            "label": {
                "en": (row.get("Label") or "").strip(),
                "it": (row.get("Label It") or "").strip(),
            },
        }
        for row in read_csv("filters.csv")
        if (row.get("Label") or row.get("Label It"))
    ]


def build_th() -> list[dict[str, object]]:
    return [
        {
            "slug": (row.get("Name") or "").strip(),
            "name": (row.get("Name") or "").strip(),
            "label": {"it": (row.get("Label It") or "").strip()},
        }
        for row in read_csv("th.csv")
        if (row.get("Name") or "").strip()
    ]


def extract_category_one_grid() -> list[dict[str, object]]:
    """Extrait l'objet JSON `criteria_groups` de la doc v3 (catégorie 1)."""
    text = (RAW / "places_api_v3.rst").read_text(encoding="utf-8")
    key = '"criteria_groups"'
    search_from = 0
    while True:
        key_index = text.find(key, search_from)
        if key_index < 0:
            break
        start = text.rfind("{", 0, key_index)
        depth = 0
        end: int | None = None
        for index in range(start, len(text)):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is not None:
            try:
                payload = json.loads(text[start:end])
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                groups = payload.get("criteria_groups")
                if groups is None and isinstance(payload.get("results"), dict):
                    groups = payload["results"].get("criteria_groups")
                if isinstance(groups, list) and groups:
                    return groups
        search_from = key_index + 1
    raise ValueError("Bloc criteria_groups introuvable dans la doc v3")


def write_json(name: str, data: object) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    categories = build_categories()
    criteria = build_criteria()
    filters = build_filters()
    th = build_th()
    grid = extract_category_one_grid()

    write_json("categories.json", categories)
    write_json("criteria.json", criteria)
    write_json("filters.json", filters)
    write_json("th.json", th)
    write_json("category_grids/category-1.json", grid)

    print(
        f"categories={len(categories)} criteria={len(criteria)} "
        f"filters={len(filters)} th={len(th)} groups={len(grid)}"
    )


if __name__ == "__main__":
    main()
