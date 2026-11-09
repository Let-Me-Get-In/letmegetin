"""Deduplication scoring: normalize a place name and bucket a similarity score.

Stdlib only (``difflib``): sufficient at import scale and needs no new dependency.
Thresholds are product decisions: auto ≥ 0.90, review ≥ 0.75. The review floor was
raised from 0.60 after measuring the national queue: 18 987 of 35 901 pairs sat in
0.60–0.70 and were mostly shared trade words ("ZOZAN KEBAB" vs "Antalya Kebab").

Names frequently end with their own town, and two neighbours 50 m apart always share
one, so the town alone lifted unrelated shops over the floor ("FNAC Bordeaux" vs
"ALDI Bordeaux" scored 0.769). Callers that know the town pass it as a normalized
``locality`` and it is stripped from the name before comparison.
"""

from __future__ import annotations

import difflib
import re
import unicodedata

from letmegetin.domain.places.entities import MatchKind

AUTO_MATCH_THRESHOLD = 0.90
REVIEW_MATCH_THRESHOLD = 0.75

# French address abbreviations that appear in raw imports ("av. de la République").
_ABBREVIATIONS: dict[str, str] = {
    "av": "avenue",
    "ave": "avenue",
    "bd": "boulevard",
    "bvd": "boulevard",
    "pl": "place",
    "st": "saint",
    "ste": "sainte",
}
_NON_WORD = re.compile(r"[^a-z0-9]+")


def normalize_name(name: str) -> str:
    """Lowercase, strip accents, expand abbreviations and collapse punctuation."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    words = _NON_WORD.sub(" ", ascii_name.lower()).split()
    return " ".join(_ABBREVIATIONS.get(word, word) for word in words)


def _compact(normalized: str) -> str:
    """Drop the separators, so a spacing or apostrophe variant is not a near miss."""
    return normalized.replace(" ", "")


def without_locality(normalized: str, locality: str) -> str:
    """Drop a trailing town name, so two neighbours are not matched on it alone.

    Only the trailing occurrence is removed: a shop that merely starts with its town
    keeps it, and a name that *is* the town is left alone.
    """
    if not locality or normalized == locality:
        return normalized
    if normalized.endswith(" " + locality):
        stripped = normalized[: -len(locality) - 1]
        return stripped or normalized
    return normalized


def similar_score(
    left: str,
    right: str,
    *,
    left_locality: str | None = None,
    right_locality: str | None = None,
) -> float:
    """Similarity in ``[0, 1]`` between two place names, both normalized first.

    ``left_locality`` and ``right_locality`` are already-normalized town names; the
    caller strips them because only it knows which place each name belongs to.
    """
    normalized_left = normalize_name(left)
    normalized_right = normalize_name(right)
    if left_locality:
        normalized_left = without_locality(normalized_left, left_locality)
    if right_locality:
        normalized_right = without_locality(normalized_right, right_locality)
    if not normalized_left or not normalized_right:
        return 0.0
    # "CocciMarket" vs "Cocci Market" and "LAPOSTROPHE" vs "L'Apostrophe" are the same
    # name; 162 national pairs differed by a separator alone and scored below 1.0.
    if _compact(normalized_left) == _compact(normalized_right):
        return 1.0
    return difflib.SequenceMatcher(None, normalized_left, normalized_right).ratio()


def classify_match(score: float) -> MatchKind:
    """Bucket a similarity score: auto link, review queue, or distinct place."""
    if score >= AUTO_MATCH_THRESHOLD:
        return "auto"
    if score >= REVIEW_MATCH_THRESHOLD:
        return "review"
    return "new"
