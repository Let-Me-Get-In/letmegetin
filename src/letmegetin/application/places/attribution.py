"""ATTRIBUTION.txt: only the sources a given ZIP actually ships, never a hard-coded list.

The text is derived from the exported rows, so OSM and Overture appear automatically the day
their rows do (phases 16-17); nothing here names a source, and there is no per-row attribution
column (D-05). Legal names and the required sentence are reviewed data: ``licences.csv``.
"""

from __future__ import annotations

from datetime import date

PRODUCED_WORKS_SENTENCE = (
    "The API and the map are Produced Works under the ODbL "
    "(attribution only, no share-alike obligation on them)."
)
FORWARD_LOOKING_SENTENCE = "Later exports may include sources not listed in this one."


def render_source_line(
    source_name: str,
    licence_name: str,
    last_update_date: date | None,
    attribution_text: str | None,
) -> str:
    """``source — licence — date`` plus the licence's reviewed sentence when it has one."""
    moment = last_update_date.isoformat() if last_update_date else "date unknown"
    line = f"{source_name} — {licence_name} — {moment}"
    if attribution_text:
        line = f"{line} — {attribution_text}"
    return line
