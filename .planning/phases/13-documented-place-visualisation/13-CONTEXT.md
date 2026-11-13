# Phase 13: Documented-place visualisation - Context

**Gathered:** 2026-11-13
**Status:** Ready for planning

<domain>
## Phase Boundary

A place shows **how well documented it is**, on one stated ladder, with an
accessible legend; an undocumented place stays visible and completable in place.

The phase delivers: the ladder (thresholds + labels + descriptions), its rendering
on the record page (overall and per handicap family), the thin opt-in on the
search endpoint that carries the same signal, and the empty-record treatment.

It does **not** change how `filled_rate` is computed (it already exists), does not
rank or filter search by documentation, does not touch licence provenance
(Phase 12, done), and does not build the export or partner surfaces (Phases 14–17).

</domain>

<decisions>
## Implementation Decisions

### The ladder
- **D-01:** **Six** levels, including both ends as first-class states:
  `0 %` Non documenté · `1–25 %` Ébauché · `26–50 %` Partiel · `51–75 %`
  Bien documenté · `76–99 %` Très documenté · `100 %` Parfaitement documenté.
  A perfect record is reachable and named, and an empty one is never presented as
  a low score of something. — **Reversibility:** costly — the labels and bounds
  become a published contract in the API and in partner-facing copy; renumbering
  them later silently changes what a stored or shared level means.
- **D-02:** The thresholds and the level slugs live **server-side, once**
  (`none | sketch | partial | good | very_good | complete`). The web layer maps a
  slug to its localized label and description; it never re-derives the level from
  the rate. One ladder, one place to change.
- **D-03:** The level is derived from the existing `filled_rate` — the share of the
  place's category-grid criteria that carry a recorded value. No new computation,
  no new denominator, no migration, no column.
- **D-04:** Each of the four handicap families gets **its own level** from the
  existing `accessibility_by_family` rates, on the same ladder. The overall level
  is the heading; family levels sit under it as four named chips, not four more
  percentages without meaning.

### Where it shows
- **D-05:** On the record page the ladder replaces the bare percentage: the
  progress bar stays, gains `aria-valuetext` with the level name, and a **static
  inline legend** lists the six levels with their bounds, always visible (no
  tooltip, no `<details>`). *Revised 2026-11-13 after critique: the per-level
  meaning line was dropped (each restated its bounds and `partial` was not
  exclusive), the single intro sentence moved above the level heading, and the
  legend became a compact list instead of six cards.*
- **D-06:** An undocumented place shows the `none` level, plus a **dedicated
  banner** at the top of the record ("Cette fiche n'est pas encore documentée")
  linking to the contribution form that already exists. It keeps appearing in
  search, unranked and unfiltered. *Revised 2026-11-13 after critique: on `none`
  the banner replaces the whole completion section (no 0 %, no bar, no family
  grid), and the link is omitted when the place has no criteria grid.*
- **D-07:** Search carries the same signal **opt-in**: `GET /api/v1/places?with_documentation=true`
  adds a `documentation` object (`rate`, `level`) to each result; absent by
  default so existing consumers pay nothing. The field is additive — the response
  stays a bare JSON array (SEARCH-03).
- **D-08:** In the search results the level renders as a **text chip**, never
  colour alone. *Revised 2026-11-13 after critique: the green border tint was
  removed — selection and hover already own the border colour, and four of the
  six dark tints were indistinguishable on the dark surface.*

### Contract and accessibility
- **D-09:** `docs/public-api.md` and the OpenAPI description document
  `with_documentation`, the six slugs and their bounds. The level is a stable
  enum, not display text.
- **D-10:** The legend has a heading and a list, the chips carry their level
  name, and the progress bar keeps `aria-valuenow` (percent) with
  `aria-valuetext` = "Level name, N %". Color never carries the only copy of the
  information. *Revised 2026-11-13 after critique: the percentage is printed once
  on the page (family chips dropped theirs), and the legend is a `ul` because the
  meanings it used to define are gone.*
- **D-11:** Six labels, the legend heading and its intro enter the single i18n
  dictionary for **fr, en** (es/de/it drafted, held until `Locale` widens);
  `check:i18n` stays a gate. *Revised 2026-11-13: descriptions dropped with the
  D-05 change, and the labels became record-centric ("Fiche complète", not
  "Parfaitement documenté") so a fully documented place whose every answer is
  "no" is not labelled as the best state in the product.*

- **D-12 (revised 2026-11-13):** *Measured defect:* `filled_rate` excluded `option`
  criteria, leaving 2 leaves, so it could only be 0 / 0.5 / 1 and three ladder
  bands never appeared on the live data. The denominator becomes the grid's
  answerable criteria (no `array` groups, no option children); family rates share
  it, filtered by family, and a family with no leaf is **absent** rather than
  0 %.
</decisions>

<agent_discretion>
## Agent's Discretion

- Exact palette step per level (one token family, contrast-checked). The search
  card carries no tint (D-08 revised).
- Family chips show the level name only; the percentage is printed once above the
  bar (D-10 revised).
- The shape of the `documentation` object beyond `rate` and `level`.

</agent_discretion>

<specifics>
## Specific Ideas

- "Parfaitement documenté" exists because a 100 % record is a real achievement
  worth naming, and because a 4- or 5-step ladder makes the top band a place where
  complete and nearly-complete places look identical.
- The ladder is a **statement about the data**, not about the place: "how well
  documented", never "how accessible". Copy must not imply the place is good.

</specifics>

<deferred>
## Deferred Ideas

- **Ranking or filtering search by documentation level** — not asked; ranking by
  documentation would punish the places most in need of contribution.
- **Moderation / confidence weighting of documentation** — a contributor can
  write one value and move a place a level; quality weighting is a later problem.
- **Per-criterion completion hints on the form** — the form already lists
  criteria; highlighting the greedy ones is a separate UX pass.

</deferred>

---

*Phase: 13-documented-place-visualisation*
*Context gathered: 2026-11-13*
