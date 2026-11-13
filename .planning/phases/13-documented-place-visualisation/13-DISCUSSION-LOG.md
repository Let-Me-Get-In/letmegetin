# Phase 13: Documented-place visualisation - Discussion Log

**Date:** 2026-11-13

## Questions asked and answers

### How many levels?
- Options presented: 3 (none / partial / complete), 4 (0 / 1–25 / 26–60 / 61–100), 5 (with a "nearly complete" band).
- Chosen: **5 levels**, then amended by the operator to **6** — adding `100 %` as
  its own "Parfaitement documenté" state.
- Consequence: the ladder has a first-class empty state and a first-class complete
  state; five intermediate percentages are not enough because "complete" and
  "nearly complete" would share a band.

### Where does it appear?
- Options presented: record page only, record + neutral text pill in search, record + colored badge in search.
- Chosen: **record page**, plus a **subtle green tint on the search-result card
  border**, with the level name always present as text.
- Answer on the API shape: the field must exist in the search response but stay
  **optional**, so a caller that does not want it does not pay for it. Adopted as
  the `with_documentation=true` opt-in (D-07).

### How are the thresholds made accessible?
- Options: static inline legend, collapsible legend, level name only.
- Chosen: **static inline legend** — always visible, no interaction, a definition
  list the screen reader can traverse.

### What does an empty record show?
- Options: 0 % + link to the form, 0 % + dedicated banner, hide the ladder entirely.
- Chosen: **0 % + dedicated banner**, never hidden. An undocumented place is the
  one that most needs a contributor.

### Do the four handicap families keep their display?
- Options: overall level + family percentages, one level per family, overall only.
- Chosen: **one level per family**, using the same ladder.

## Alternatives considered and dropped

- **Three levels** — too coarse; a 60 % and a 95 % record read the same.
- **Threshold values as reviewed CSV data** (the Phase 12 pattern) — rejected:
  there is no operator who would edit them, and they are product copy, not legal
  facts. They live in one server-side module instead (D-02).
- **Always computing documentation for every search result** — rejected: a list of
  100 places would pay an aggregate it may not need; opt-in keeps the default
  response byte-identical for existing consumers.
- **Colored badge as the only signal in search** — rejected: color alone fails
  accessibility; the tint is decorative and the level name carries the meaning.

## Open points left to the planner

- Whether the search aggregate is one SQL statement over the result ids or a
  per-category join; the phase requires no N+1.
- Exact palette step per level and the tint alpha.
- Whether the family chips also print their percentage.
