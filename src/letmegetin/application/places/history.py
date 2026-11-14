"""Per-place history folded from the export journal (D-13).

The diff is computed at read time from consecutive full-row payloads, never stored.
"""

from __future__ import annotations

from letmegetin.domain.places.export import (
    ExportEvent,
    ExportEventRepository,
    describe_changes,
)


def format_history(events: list[ExportEvent]) -> list[str]:
    """One line per event in ``seq`` order, naming the fields that moved since the previous."""
    lines: list[str] = []
    previous: dict[str, object] = {}
    for event in events:
        changed = describe_changes(previous, event.payload)
        summary = ", ".join(f"{key}={value}" for key, value in changed.items()) or "no change"
        lines.append(f"{event.occurred_at:%Y-%m-%d} {event.op} {event.actor} {summary}")
        previous = event.payload
    return lines


async def place_history(events: ExportEventRepository, slug: str) -> list[str]:
    """The whole journal of one place, ready to print; an unknown slug is not an error."""
    found = await events.list_events_by_slug(slug)
    if not found:
        return [f"no history yet for {slug}"]
    return format_history(found)
