"""Deduplication scoring: normalize a place name and bucket a similarity score.

Stdlib only (``difflib``): sufficient at import scale and needs no new dependency.
Thresholds are product decisions: auto ≥ 0.90, review ≥ 0.75. The review floor was
raised from 0.60 after measuring the national queue: 18 987 of 35 901 pairs sat in
0.60–0.70 and were mostly shared trade words ("ZOZAN KEBAB" vs "Antalya Kebab").
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


def similar_score(left: str, right: str) -> float:
    """Similarity in ``[0, 1]`` between two place names, both normalized first."""
    normalized_left = normalize_name(left)
    normalized_right = normalize_name(right)
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
