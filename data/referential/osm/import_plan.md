# LetMeGetIn — OpenStreetMap import plan

This document is part of the automated-edit proposal for OpenStreetMap. It describes exactly what
LetMeGetIn imports from OSM and what it writes back. It is reviewed data: the tag mapping it names
lives in `data/referential/`, not in code.

## What we import

The **Geofabrik France extract** (`france-latest.osm.pbf`), read in streaming. Every tagged node and
way is a candidate; nothing is downloaded from the OSM API, no Overpass query is issued, and no OSM
editor is touched.

- Imported rows carry `source='osm'` and keep the object reference as their identifier
  (`node/123`, `way/456`), so a re-run updates the same row instead of duplicating it.
- An imported row keeps the object's **full raw tag set** and its **version**. We re-emit both when
  we write back, because an `.osmChange` `<modify>` replaces the whole object: dropping a tag we
  never mapped would delete live data.

## Why we import it

OSM is our community base. The point is to hold the places that are *not yet documented* for
accessibility — a bakery with no `wheelchair` tag is exactly the kind of place a contributor can
complete on LetMeGetIn, and we want it visible rather than absent. We import all POIs in the mapped
categories, not only those already carrying accessibility tags.

## Scope

Only the categories an operator has explicitly mapped are imported. The bridge is the reviewed
`osm_tag` column of `data/referential/category_mapping.csv`; a POI whose tags match no reviewed row
is **skipped and counted**, never guessed. The import report prints the most frequent unmatched tag
combinations, so the mapping grows from evidence rather than opinion.

Accessibility values come from the reviewed `data/referential/osm_accessibility_tags.csv`: one row
per `(osm_key, osm_value)` pair mapped onto one of our criteria and that criterion's own typed value.
A tag pair the review did not map is dropped, never coerced.

## Method

- **Streaming**, never materialised: the PBF is read object by object, because the national extract
  does not fit in memory.
- **Idempotent** on `(source, source_id)`: a second run changes nothing, a changed object updates in
  place.
- **Deduplication is internal.** We never query an external API to find duplicates. The Phase-3
  scorer runs against our own database — 100 m spatial blocking, normalised-name similarity, an auto
  link at ≥ 0.90, a review queue between 0.75 and 0.90. A matched row is *linked* (canonical id set,
  OSM name kept as an alias, merge logged); nothing is ever deleted or hard-merged.
- **Provenance is stamped** on every row: `source='osm'`, the ODbL licence, the retrieval time.

## Write-back policy

We generate an `.osmChange` document for an operator to review and upload; we do not run an
automated uploader. The generator refuses to write anything unless every policy artefact and an
explicit, human-granted terms-of-service consent are present, and it only ever modifies objects we
already hold a version and a full tag set for. Nothing is created, nothing is deleted.

## Throttle

`OSM_THROTTLE_SECONDS` (defined in `src/letmegetin/application/places/osm_publish.py`) is the
operator-adjustable delay between successive API requests: no published OSM quota exists, so the
rate is a reviewed constant rather than a guess scattered through the code. The future uploader
reads this value; nothing in the generator sleeps on it, because the generator writes a file and
makes no network call.

## Licence

OSM data is ODbL 1.0. Anything derived from it stays ODbL and is never sent to a destination that
cannot carry the share-alike obligation — the redistribution matrix in
`data/referential/licence_destinations.csv` refuses `odbl` towards a Licence Ouverte partner, and
that rule is data, not a branch.
