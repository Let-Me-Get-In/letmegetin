"""Petits utilitaires partagés."""

from __future__ import annotations

import re
import unicodedata


def slugify(value: str) -> str:
    """Transforme un libellé en slug ASCII stable."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "item"
