---
url: <to be published>
---

# LetMeGetIn — accessibility contributions to OpenStreetMap

LetMeGetIn (https://letmegetin.org) is a public, open-source accessibility guide for places in
France. It is the modern rewrite of Jaccede: one normalised accessibility referential, exposed as a
public API and contributed to by people who know a place.

This page documents what we import from OpenStreetMap and what we propose to write back. It follows
the [[Import/Plan Outline]] and the [[FR:Import/Guidelines]].

**Status: proposal.** Nothing has been uploaded. The repository generates an `.osmChange` file for a
human to review; there is no automated uploader and no edit is made without the discussion below
being closed.

## Goals

OSM is our community base, and its accessibility gaps are exactly what LetMeGetIn exists to fill.

- **Import:** hold the places that are *not yet documented* for accessibility. A bakery with no
  `wheelchair` tag is a place a contributor can complete — but only if it is visible on our map.
- **Write back:** return the accessibility answers our contributors record for those places, as OSM
  tags, so the work benefits OSM too.

We do not duplicate OSM, we do not compete with it, and we do not overwrite what mappers have
surveyed by hand — a human answer in OSM always wins over ours.

## Schedule

Nothing is scheduled until this proposal is accepted. The first upload, if accepted, will be a single
reviewed changeset of a few dozen objects, announced in the discussion thread before it is made.

## Import Data

### Background

- Source: the **Geofabrik France extract**, `france-latest.osm.pbf` (https://download.geofabrik.de/europe/france.html).
- Licence: **ODbL 1.0** — the same licence as OSM, so the round trip adds no licensing constraint.
- Extraction: none. We read every tagged object and keep the OSM identifiers as they are.
- Our code is AGPL-3.0 and public: https://github.com/Let-Me-Get-In/letmegetin

### OSM Data Files

The national extract, read in streaming. Nothing is fetched from the OSM API and no Overpass query is
issued.

### Import Type

**One-time manual upload, then recurring manual uploads of small changesets.** Not a bot run, not a
continuous sync. An operator reviews a generated `.osmChange` document and sends it from a dedicated
account (see [[#Changeset Tags]]).

## Data Preparation

### Data Reduction & Simplification

No geometry is created, simplified or removed: we only ever *modify* existing objects, and we keep
their identifiers and versions.

### Tagging Plans

Two reviewed files drive everything, and both are data, never code:

- `category_mapping.csv` — which OSM tag maps to which of our categories (currently 124 of our 158
  categories resolved);
- `osm_accessibility_tags.csv` — which OSM accessibility tag pair maps to which of our criteria
  values.

A POI whose tags match no reviewed row is **skipped and counted**, never guessed. The import report
publishes the most frequent unmatched tag combinations, so the mapping grows from evidence.

On the write-back side, we add only tags a reviewed row can express. The mapping is deliberately
conservative: values we cannot map legally are left alone rather than approximated — for instance
`wheelchair=no`, `ramp`, `handrail` and `hearing_loop` are **not** mapped today, because our
referential has no criterion that can carry them without inventing meaning.

### Changeset Tags

- `comment` = `LetMeGetIn accessibility contribution — see <this page>`
- `created_by` = `LetMeGetIn <version>`
- `source` = `survey` for answers recorded in the field by a contributor; the generated document
  records the provenance per answer so the operator can state it accurately.

Changeset size is capped by the review workflow, not by the tool: an operator sends one reviewed
batch at a time. No changeset will exceed a few hundred objects.

### Data Transformation

The generator re-emits the object's **full stored tag set** with our accessibility tags added,
because an `.osmChange` `<modify>` replaces the whole tag set — omitting a tag would delete it. An
object whose version or raw tag set we do not hold is **not emitted and is counted**: we would rather
skip a place than damage it.

Nothing is ever created and nothing is ever deleted.

### Data Transformation Results

The generated document is a plain `.osmChange` file plus a one-line changeset comment, both left
beside each other for review. It is not published anywhere automatically.

## Data Merge Workflow

### Team Approach

One operator, reviewed by hand. Sébastien Billion (contact below) is the maintainer.

### Workflow

1. A contributor records an accessibility answer on LetMeGetIn for a place we imported from OSM.
2. `osm publish` refuses to run unless every policy artefact and an explicit, human-granted
   contributor-terms consent are present, and it only ever emits objects we hold a version and a full
   tag set for.
3. The operator opens the generated `.osmChange` in JOSM, checks the objects, and uploads.
4. Every changeset links this page.

### Conflation

Deduplication is **internal**, against our own database — we never query an external API to find a
match, and we never merge in OSM.

When we import, a candidate within 100 m whose normalised name scores ≥ 0.90 is *linked* to our
canonical row (identifier kept, name kept as an alias, merge logged); between 0.75 and 0.90 it goes to
a review queue. Nothing is ever deleted or hard-merged on either side. A linked OSM object is still
emitted under its own node id: we modify the OSM object that exists, never our canonical placeholder.

## QA

- Every answer written back is validated before it leaves: a null or out-of-type value is refused,
  never coerced — a null would delete the OSM tag.
- Freshness is compared first: if OSM's object is newer than our answer, we skip and journal the
  decision. A re-run of the same batch patches nothing.
- Every attempt is journalled with the losing value kept, so a mistaken write can be traced and
  reverted object by object.
- The generator refuses to write at all if a policy artefact is missing or invalid.

## Discussion

- Discussion thread: **<to be published>**
- French OSM forum: https://forum.openstreetmap.fr/
- French mailing list: https://lists.openstreetmap.org/listinfo/talk-fr

Discussion is open and this page will record its outcome before any upload happens.

## Contact

Sébastien Billion — contact@letmegetin.org — https://letmegetin.org
