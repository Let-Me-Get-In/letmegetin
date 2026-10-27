"""Admin use cases: curate the referential (vocabulary, categories, criteria, mapping)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from letmegetin.core.exceptions import DomainError
from letmegetin.domain.referential.entities import VocabularyEntry
from letmegetin.domain.referential.repositories import VocabularyRepository


@dataclass
class ImportReport:
    """Outcome of a vocabulary import: rows created and rows already present."""

    created: int
    skipped: int


def load_vocabulary_file(path: Path) -> list[VocabularyEntry]:
    """Read a JSON list of ``{slug, label, description}`` objects into vocabulary entries."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries: list[VocabularyEntry] = []
    for item in raw:
        slug = item.get("slug")
        if not slug:
            raise DomainError("vocabulary entry is missing a slug")
        label = item.get("label") or {}
        if not label:
            raise DomainError(f"vocabulary entry '{slug}' has no label")
        entries.append(
            VocabularyEntry(
                id=0,
                slug=slug,
                label=label,
                description=item.get("description") or {},
            )
        )
    return entries


async def import_vocabulary(
    repository: VocabularyRepository, entries: list[VocabularyEntry]
) -> ImportReport:
    """Upsert vocabulary entries by slug; existing slugs are left untouched."""
    created = 0
    skipped = 0
    for entry in entries:
        if await repository.get_by_slug(entry.slug) is not None:
            skipped += 1
            continue
        await repository.add(entry)
        created += 1
    return ImportReport(created=created, skipped=skipped)
