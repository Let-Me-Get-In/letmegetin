"""Deduplication scoring unit tests (pure, no database)."""

from __future__ import annotations

import pytest

from letmegetin.domain.places.dedup import (
    AUTO_MATCH_THRESHOLD,
    REVIEW_MATCH_THRESHOLD,
    classify_match,
    normalize_name,
    similar_score,
)

_NORMALIZATION = [
    ("Musée du Louvre", "musee du louvre"),
    ("  Café   de Flore  ", "cafe de flore"),
    ("Boulangerie St-Michel", "boulangerie saint michel"),
    ("av. de la République", "avenue de la republique"),
    ("bd Voltaire", "boulevard voltaire"),
    ("L'Atelier", "l atelier"),
    ("", ""),
    ("!!!", ""),
]


@pytest.mark.parametrize(
    ("raw", "expected"), _NORMALIZATION, ids=[raw for raw, _ in _NORMALIZATION]
)
def test_normalize_name(raw: str, expected: str) -> None:
    assert normalize_name(raw) == expected


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("Musée du Louvre", "Musee du Louvre"),
        ("CocciMarket", "Cocci Market"),
        ("CocciMarket", "COCCIMARKET"),
        ("LAPOSTROPHE", "L'Apostrophe"),
        ("Vert Baudet", "Vertbaudet"),
        ("Truffes Folies", "Truffesfolies"),
    ],
    ids=["accent", "space", "case-and-space", "apostrophe", "company-space", "plural-space"],
)
def test_similar_score_is_one_for_normalized_equality(left: str, right: str) -> None:
    assert similar_score(left, right) == 1.0


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("ZOZAN KEBAB", "Antalya Kebab"),
        ("ZONE KEBAB", "Sultan Kebab"),
        ("Zoe coiffure", "Stephane coiffure"),
    ],
    ids=["different-name", "different-name-2", "shared-trade-word"],
)
def test_a_shared_trade_word_does_not_reach_the_review_band(left: str, right: str) -> None:
    # Measured on the national queue: 18 987 pairs sat in 0.60-0.70 and were mostly
    # two different shops whose names share a trade word.
    assert similar_score(left, right) < REVIEW_MATCH_THRESHOLD


@pytest.mark.parametrize(
    ("left", "right", "minimum", "maximum"),
    [
        ("Musée du Louvre", "Musee du Louvre Paris", 0.8, 0.9),
        ("Café de Flore", "Pharmacie du Coin", 0.0, 0.5),
        ("", "Café de Flore", 0.0, 0.0),
    ],
    ids=["prefix-variant", "unrelated", "empty"],
)
def test_similar_score_stays_in_its_bucket(
    left: str, right: str, minimum: float, maximum: float
) -> None:
    assert minimum <= similar_score(left, right) <= maximum


def test_similar_score_is_symmetric() -> None:
    assert similar_score("Musée du Louvre", "Louvre Museum") == similar_score(
        "Louvre Museum", "Musée du Louvre"
    )


@pytest.mark.parametrize(
    ("score", "kind"),
    [
        (1.0, "auto"),
        (AUTO_MATCH_THRESHOLD, "auto"),
        (0.95, "auto"),
        (0.89, "review"),
        (0.74, "new"),
        (REVIEW_MATCH_THRESHOLD, "review"),
        (0.59, "new"),
        (0.0, "new"),
    ],
    ids=[
        "exact",
        "auto-threshold",
        "high",
        "just-below-auto",
        "review-threshold",
        "just-below-review",
        "low",
        "zero",
    ],
)
def test_classify_match(score: float, kind: str) -> None:
    assert classify_match(score) == kind
