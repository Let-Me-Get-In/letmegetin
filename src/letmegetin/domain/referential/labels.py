"""Multilingual label helpers (pure: no I/O, no SQLAlchemy)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from letmegetin.core.exceptions import LabelError
from letmegetin.domain.referential.entities import Label

SUPPORTED_LOCALES: tuple[str, ...] = ("fr", "en", "es", "de", "it")


def parse_label_pairs(pairs: Sequence[str]) -> Label:
    """Parse ``locale=value`` pairs, rejecting unknown locales and missing separators."""
    parsed: Label = {}
    for pair in pairs:
        locale, separator, value = pair.partition("=")
        if not separator:
            raise LabelError(f"label '{pair}' must look like 'locale=value'")
        locale = locale.strip().lower()
        if locale not in SUPPORTED_LOCALES:
            supported = ", ".join(SUPPORTED_LOCALES)
            raise LabelError(f"unsupported locale '{locale}' (supported: {supported})")
        parsed[locale] = value.strip()
    return normalize_label(parsed)


def normalize_label(label: Mapping[str, str]) -> Label:
    """Keep only supported locales with a non-empty trimmed value."""
    return {
        locale: str(label[locale]).strip()
        for locale in SUPPORTED_LOCALES
        if locale in label and str(label[locale]).strip()
    }


def merge_label(current: Mapping[str, str], overrides: Mapping[str, str]) -> Label:
    """Override only the locales present in ``overrides``, keeping the others."""
    merged = normalize_label(current)
    merged.update(normalize_label(overrides))
    return merged
