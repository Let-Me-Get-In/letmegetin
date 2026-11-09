"""Tests for slugify (pure utilities, no database)."""

from __future__ import annotations

import pytest

from letmegetin.core.utils import slugify


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ENTRÉE", "entree"),
        ("a b/c", "a-b-c"),
        ("!!!", "item"),
        ("  École   primaire  ", "ecole-primaire"),
        ("Déjà-slug", "deja-slug"),
    ],
    ids=["accent", "separators", "empty", "collapse", "idempotent"],
)
def test_slugify(value: str, expected: str) -> None:
    assert slugify(value) == expected
