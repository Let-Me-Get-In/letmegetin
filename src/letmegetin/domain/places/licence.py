"""Redistribution rule: may a row under a licence leave towards a destination?

The rule is reviewed data — ``licence_destination`` rows loaded from
``data/referential/licence_destinations.csv`` — so this module names no licence and
holds no per-pair branch: LIC-03 (never ``odbl`` to ``lov2_partner``) is a row, not
code. Stdlib only, like ``dedup.py``; the SQL twin in the repository is the same
predicate pushed down for bulk extraction (D-13).
"""

from __future__ import annotations

from collections.abc import Mapping

# The closed set the reviewed matrix may address (D-06); a CheckConstraint backs it.
DESTINATIONS: tuple[str, ...] = ("open_export", "osm", "lov2_partner")


def can_redistribute(
    licence: str | None,
    destination: str,
    matrix: Mapping[tuple[str, str], bool] | None = None,
) -> bool:
    """Whether a row under ``licence`` may leave towards ``destination`` (D-13).

    Fail-closed (D-15): a NULL licence, a pair absent from the matrix and an absent
    matrix are all refused, so an unreviewed licence never opens an exit path.
    """
    if licence is None or matrix is None:
        return False
    return bool(matrix.get((licence, destination)))
