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
  inline legend** lists all six levels with their bounds and one line of meaning,
  always visible (no tooltip, no `<details>`).
- **D-06:** An undocumented place shows `0 %` and the `none` level, plus a
  **dedicated banner** at the top of the record ("Cette fiche n'est pas encore
  documentée") linking to the contribution form that already exists. It keeps
  appearing in search, unranked and unfiltered.
- **D-07:** Search carries the same signal **opt-in**: `GET /api/v1/places?with_documentation=true`
  adds a `documentation` object (`rate`, `level`) to each result; absent by
  default so existing consumers pay nothing. The field is additive — the response
  stays a bare JSON array (SEARCH-03).
- **D-08:** In the search results the level renders as a subtle **green tint on
  the card border**, never color alone: the level name is always present as text
  and the tint is decorative. Contrast is checked against the existing tokens.

### Contract and accessibility
- **D-09:** `docs/public-api.md` and the OpenAPI description document
  `with_documentation`, the six slugs and their bounds. The level is a stable
  enum, not display text.
- **D-10:** The legend is a definition list (`<dl>`), the chips carry their level
  name plus the percentage, and the progress bar keeps `aria-valuenow` (percent)
  with `aria-valuetext` = "Level name, N %". Color never carries the only copy of
  the information.
- **D-11:** Six labels, six one-line descriptions and the legend heading enter the
  single i18n dictionary for **fr, en, es, de, it**; `check:i18n` stays a gate.

</decisions>

<agent_discretion>
## Agent's Discretion

- Exact palette step per level (one token family, contrast-checked) and the tint
  alpha on the search card border.
- Whether the family chips show the percentage alongside the level name (D-04
  says named chips; the number is optional if the chip stays readable).
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
