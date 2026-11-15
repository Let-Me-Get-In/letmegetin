# Phase 15 — Discussion Log

**Phase:** AccesLibre round trip
**Date:** 2026-11-15
**Mode:** discuss (interactive, one question group per area)

---

## Area 1 — Licence of the contributions

**Why it mattered:** the matrix says `odbl × lov2_partner = false` and `source_licences.csv` says
`user → odbl`, so the lov2 feed would have carried zero contributions. Without a licence decision the
whole phase degenerates into a freshness mirror.

**Options presented:**
1. New `dual` slug (lov2 + ODbL), `user → dual` — *chosen*
2. Switch `user → lov2` outright
3. Keep `odbl`, feed without contributions

**User selection:** all three were selected in the first pass — mutually exclusive. Put back as
"which package", the user confirmed **dual**.

**Rationale recorded:** dual keeps the open export's share-alike guarantee while making the rows
shippable to a lov2 destination. Flatly switching to lov2 would give up ODbL on community data
without changing the terms the contributor agreed to.

---

## Area 2 — Extent of the criterion mapping

**Options presented:**
1. The 8 fields that carry data — *chosen*
2. The 19 answerable criteria
3. All 61 reference criteria

**User selection:** all three, then confirmed **8**.

**Rationale recorded:** the 8 `FIELD_MAP` columns are also the only criteria with values across the
634 931 imported places; the other 11 answerable criteria are empty nationally, so mapping them today
would be dead work. The mapping document lists them explicitly as "not yet expressible" rather than
dropping them silently.

---

## Area 3 — Conflict rule at push time

**Options presented:**
1. Freshness + journal, as Phase 12 — *chosen*
2. Blind PATCH
3. Read then diff

**User selection:** all three again. Option 3 is not alternative to option 1 — it is how option 1 is
implemented — so the coherent reading (read, diff, then apply the freshness rule and journal every
attempt) was adopted and recorded as D-10 + D-11 + D-12.

**Note:** option 2 was rejected because it would overwrite a correction made upstream after our import.

---

## Area 4 — Shape of the unmappable-places document

**Options presented:**
1. Reviewed CSV + a section in `docs/` — *chosen*
2. Markdown only
3. CSV + an API route

**User selection:** all three, then confirmed **CSV + docs**, without the route.

**Rationale recorded:** the CSV follows the existing reviewed-data convention (`families.csv`,
`licences.csv`) and stays auditable; the route has no consumer yet and was moved to Deferred.

---

## Scope question

After four areas where every option was selected, the portée was put back as three coherent packages:

1. **Maximal coherent package** — dual licence, 8 fields shipped with the rest documented, push as
   GET-then-diff with freshness + journal, CSV + docs — *chosen*
2. Everything including the 61-criterion table and an API route
3. Feed only, push deferred until a key exists

**Rationale recorded:** package 2 is a multi-day data project on top of the code, and package 3 would
leave PART-02 unbuilt while the partnership is being negotiated.

---

## Deferred during the discussion

- 61-criterion mapping table (data project)
- API route for the mapping document (no consumer)
- Scheduled delivery to AccesLibre (ops, needs the key)
- Pushing to OSM (Phase 16)

## Agent's discretion

- Archive naming for the partner destination
- Diff on raw CSV values vs parsed typed values
- Mapping CSV column layout, provided entity + reason + identifier are present
- Rate limiting and retry policy (no published quota)

## Canonical references surfaced during discussion

- `data/referential/acceslibre_categories.csv` (391 rows)
- `src/letmegetin/domain/places/acceslibre_map.py` (`FIELD_MAP`, 8 entries)
- `src/letmegetin/application/places/import_acceslibre.py` (`_COLUMNS`)
- `https://acceslibre.beta.gouv.fr/api/docs/`
- `https://acceslibre.beta.gouv.fr/contact/api_key/`
- `.planning/phases/15-acceslibre-round-trip/15-PARTNER-ASK.md`
