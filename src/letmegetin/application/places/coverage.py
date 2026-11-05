"""Coverage export: places and accessibility fill rate per category and country (DATA-04).

Read-only: one aggregate query, so the export is safe to run on production and the CSV
only carries aggregated counts (no user, review or contact data).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from dataclasses import dataclass

from letmegetin.domain.places.repositories import CoverageRepository

COVERAGE_HEADER = ("category", "country", "places", "with_accessibility", "fill_rate")


@dataclass
class CoverageRow:
    """One (category, country) bucket plus the totals row."""

    category: str
    country: str
    places: int
    with_accessibility: int
    fill_rate: float = 0.0


def _rate(with_accessibility: int, places: int) -> float:
    return round(with_accessibility / places, 3) if places else 0.0


async def coverage(coverage_repo: CoverageRepository) -> list[CoverageRow]:
    """Aggregate rows with their fill rate, followed by a totals row (empty when no places)."""
    rows = [
        CoverageRow(
            category=category,
            country=country,
            places=places,
            with_accessibility=with_accessibility,
            fill_rate=_rate(with_accessibility, places),
        )
        for category, country, places, with_accessibility in (
            await coverage_repo.by_category_country()
        )
    ]
    if rows:
        places = sum(row.places for row in rows)
        with_accessibility = sum(row.with_accessibility for row in rows)
        rows.append(
            CoverageRow(
                category="total",
                country="",
                places=places,
                with_accessibility=with_accessibility,
                fill_rate=_rate(with_accessibility, places),
            )
        )
    return rows


def coverage_csv(rows: Iterable[CoverageRow]) -> str:
    """CSV text (quoted through the csv module, never string concatenation)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COVERAGE_HEADER)
    for row in rows:
        writer.writerow(
            [row.category, row.country, row.places, row.with_accessibility, row.fill_rate]
        )
    return buffer.getvalue()


def coverage_table(rows: Iterable[CoverageRow]) -> str:
    """Tab-separated table for a terminal."""
    lines = ["\t".join(COVERAGE_HEADER)]
    lines.extend(
        f"{row.category}\t{row.country}\t{row.places}\t{row.with_accessibility}"
        f"\t{row.fill_rate:.3f}"
        for row in rows
    )
    return "\n".join(lines)
