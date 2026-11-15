# Phase 16: OpenStreetMap - Discussion Log

**Session:** 2026-11-15
**Mode:** discuss (interactive)

## Scout findings

- `category_mapping.csv` already carries an `osm_tag` column: 34 of 158 categories are filled
  (`tourism=camp_site`, `shop=bakery`, `amenity=parking`, …).
- `source_licences.csv` holds only `acceslibre→lov2` and `user→dual`; no OSM row exists.
- No OSM client, importer or dependency exists. `httpx` is available; a PBF reader is not.
- The dedup machinery is source-agnostic and already measured (100 m blocking, `difflib` scoring,
  18 987 pairs in the 0.60–0.70 band before the floor was raised to 0.75).
- No place-creation endpoint exists: contributing edits an existing place's criteria only.

## Questions asked and answers

### 1. Where does the OSM data come from?
**Options:** Geofabrik PBF + `pyosmium` · Overpass API · a pre-filtered file.
**Answered:** Geofabrik PBF + `pyosmium`. The reasoning recorded: streaming is what makes a national
import feasible; Overpass is not built for 600k objects and every query costs the community.

### 2. What does phase 16 deliver?
**Options:** import complete + publication behind a human gate · import + publication coded but not
activated · import only.
**Answered:** import + publication **coded, not activated**. The changeset generator, throttle and
policy artefacts are built and tested against a fake server; nothing is uploaded.

### 3. Which OSM subset to import?
The first answer was a hesitation between "only accessibility-tagged POIs" and "all mapped
categories", with a concrete objection: duplicates against AccesLibre and Overture are a real
problem, and the goal is to have undocumented places to fill.

Rather than picking, the mechanism was explained and the answer followed:
**all POIs in the mapped categories**, because the point of the phase is undocumented places.

The duplicate concern was answered with evidence, not reassurance: no external API is needed.
Dedup is internal and already shipped — 100 m blocking, normalised-name scoring with the town
stripped, auto-link ≥ 0.90, review 0.75–0.90, nothing deleted. A third source produces linked rows,
not duplicates. The `candidates` endpoint already answers "did you mean X?" against every source at
once.

### 4. Where do "filter places with no criteria" and "add a place" go?
**Answered:** separate tickets, outside phase 16. Both are front work; neither exists today (there
is no place-creation endpoint at all), and folding them in would mix a backend phase with a front
one.

### 5. Which OSM tags feed our criteria?
**Answered:** categories **and** accessibility tags — two reviewed files, not one.

## Alternatives considered and rejected

- **Overpass API instead of a PBF extract.** Rejected: quotas, timeouts, and a cost paid by the
  community for a national-scale read.
- **Import only accessibility-tagged POIs.** Rejected: it fills the database with places that are
  already documented elsewhere and leaves the undocumented ones out — the opposite of the goal.
- **Live OSM uploader in this phase.** Rejected: OSM's automated-edit policy requires a wiki page,
  a community discussion and a bot account before a single changeset; building the uploader before
  approval would produce code that must never run.
- **Checking duplicates against each source's API.** Rejected: unnecessary, and it would make the
  import depend on three external services being up.
- **Putting the map filter and place creation in phase 16.** Rejected: it is front work with no
  dependency on OSM.
