"""Emit candidate duplicates from an AccesLibre export, with the evidence, for the partner.

The export is post-cleanup, so a pair we can still see is a pair their own rule missed.
This script does not touch their base: it writes a CSV a human can review.

    uv run python scripts/acceslibre_duplicate_candidates.py acceslibre.csv out.csv

Verdicts: `meme_batiment` and `meme_adresse` are worth their attention; `a_examiner` has
neither proof; pairs whose two known RNB ids differ are dropped and only counted.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from letmegetin.domain.places.dedup import REVIEW_MATCH_THRESHOLD, similar_score  # noqa: E402

_METRES_PER_DEGREE = 111_320.0
_LATITUDE_SHRINK = 0.62  # matches the application dedup pass, so both count the same pairs
_RADIUS_M = 50.0
_CELL_LAT = _RADIUS_M / _METRES_PER_DEGREE
_CELL_LNG = _RADIUS_M / (_METRES_PER_DEGREE * _LATITUDE_SHRINK)


def _load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            try:
                float(row["latitude"]), float(row["longitude"])
            except (KeyError, TypeError, ValueError):
                continue
            rows.append(row)
    return rows


def _distance_m(left: dict[str, str], right: dict[str, str]) -> float:
    dy = (float(left["latitude"]) - float(right["latitude"])) * _METRES_PER_DEGREE
    dx = (
        (float(left["longitude"]) - float(right["longitude"]))
        * _METRES_PER_DEGREE
        * _LATITUDE_SHRINK
    )
    return (dx * dx + dy * dy) ** 0.5


def _address(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        (row.get("numero") or "").strip().lower(),
        (row.get("voie") or "").strip().lower(),
        (row.get("commune") or "").strip().lower(),
    )


def _verdict(left: dict[str, str], right: dict[str, str]) -> str | None:
    rnb_left = (left.get("rnb_id") or "").strip()
    rnb_right = (right.get("rnb_id") or "").strip()
    if rnb_left and rnb_right and rnb_left != rnb_right:
        return None
    if rnb_left and rnb_left == rnb_right:
        return "meme_batiment"
    number, street, commune = _address(left)
    if number and (number, street, commune) == _address(right):
        return "meme_adresse"
    return "a_examiner"


def candidates(rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], int]:
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        grid[
            (int(float(row["latitude"]) / _CELL_LAT), int(float(row["longitude"]) / _CELL_LNG))
        ].append(index)

    out: list[dict[str, object]] = []
    dropped = 0
    for (lat_cell, lng_cell), members in grid.items():
        neighbours = [
            index
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            for index in grid.get((lat_cell + dy, lng_cell + dx), ())
        ]
        for left_index in members:
            left = rows[left_index]
            for right_index in neighbours:
                if right_index <= left_index:
                    continue
                right = rows[right_index]
                distance = _distance_m(left, right)
                if distance > _RADIUS_M:
                    continue
                score = similar_score(
                    left["name"],
                    right["name"],
                    left_locality=left.get("commune"),
                    right_locality=right.get("commune"),
                )
                if score < REVIEW_MATCH_THRESHOLD:
                    continue
                verdict = _verdict(left, right)
                if verdict is None:
                    dropped += 1
                    continue
                out.append(
                    {
                        "verdict": verdict,
                        "score": round(score, 3),
                        "distance_m": round(distance, 1),
                        "id_a": left["id"],
                        "nom_a": left["name"],
                        "adresse_a": " ".join(
                            part
                            for part in (
                                (left.get("numero") or "").strip(),
                                (left.get("voie") or "").strip(),
                            )
                            if part
                        ),
                        "commune_a": left.get("commune") or "",
                        "rnb_a": (left.get("rnb_id") or "").strip(),
                        "id_b": right["id"],
                        "nom_b": right["name"],
                        "adresse_b": " ".join(
                            part
                            for part in (
                                (right.get("numero") or "").strip(),
                                (right.get("voie") or "").strip(),
                            )
                            if part
                        ),
                        "commune_b": right.get("commune") or "",
                        "rnb_b": (right.get("rnb_id") or "").strip(),
                        "activite": left.get("activite") or "",
                    }
                )
    out.sort(key=lambda row: (str(row["verdict"]), -float(str(row["score"]))))
    return out, dropped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    rows = _load(args.export)
    found, dropped = candidates(rows)
    assert all(float(str(row["score"])) >= REVIEW_MATCH_THRESHOLD for row in found), "score floor"

    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(found[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(found)

    counts: dict[str, int] = defaultdict(int)
    for row in found:
        counts[str(row["verdict"])] += 1
    print(f"{len(rows)} fiches lues, {len(found)} paires candidates, {dropped} exclues")
    for verdict, count in sorted(counts.items()):
        print(f"  {verdict}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
