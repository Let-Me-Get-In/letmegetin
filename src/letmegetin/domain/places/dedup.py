"""Deduplication scoring: normalize a place name and bucket a similarity score.

Stdlib only (``difflib``): sufficient at import scale and needs no new dependency.
Thresholds are the product decisions from 03-CONTEXT.md (auto ≥ 0.90, review ≥ 0.60).
"""

from __future__ import annotations

import difflib
import re
import unicodedata

from letmegetin.domain.places.entities import MatchKind

AUTO_MATCH_THRESHOLD = 0.90
REVIEW_MATCH_THRESHOLD = 0.60

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


def similar_score(left: str, right: str) -> float:
    """Similarity in ``[0, 1]`` between two place names, both normalized first."""
    normalized_left = normalize_name(left)
    normalized_right = normalize_name(right)
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left == normalized_right:
        return 1.0
    return difflib.SequenceMatcher(None, normalized_left, normalized_right).ratio()


def classify_match(score: float) -> MatchKind:
    """Bucket a similarity score: auto link, review queue, or distinct place."""
    if score >= AUTO_MATCH_THRESHOLD:
        return "auto"
    if score >= REVIEW_MATCH_THRESHOLD:
        return "review"
    return "new"
