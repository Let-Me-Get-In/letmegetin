---
url: <to be published>
---

# LetMeGetIn — accessibility contributions to OpenStreetMap

LetMeGetIn (https://letmegetin.org) is a public, open-source accessibility guide for places in
France. It is the modern rewrite of Jaccede: one normalised accessibility referential, exposed as a
public API and contributed to by people who know a place. This page documents what we import from
OpenStreetMap and what we propose to write back, as OSM's automated-edit policy requires.

## What we import

The Geofabrik France extract (`france-latest.osm.pbf`), read in streaming. We import every POI in
the categories an operator has explicitly mapped to an OSM tag — not only the places that already
carry accessibility tags. The point is the opposite: a place with no accessibility data is a place
a contributor can complete.

Two reviewed files drive everything, and both are data, never code:

- `category_mapping.csv` — which OSM tag maps to which of our categories;
- `osm_accessibility_tags.csv` — which OSM accessibility tag pair (`wheelchair`, `toilets:wheelchair`,
  …) maps to which of our criteria values.

A POI whose tags match no reviewed row is skipped and counted. We never guess a category or a value,
and we publish the most frequent unmatched tag combinations so the mapping can grow from evidence.

## What we write back

Only accessibility answers our own contributors recorded for an OSM place, and only when a reviewed
row can express them as an OSM tag. A write-back is a `<modify>` of an object we already hold: we
re-emit the object's full stored tag set with our tags added, because OSM replaces the whole tag set
— omitting a tag would delete it. We never create objects, never delete any, and never touch an
object whose version or raw tags we do not hold.

The changeset comment follows one reviewed template, so a reviewer can always find this page:

    LetMeGetIn accessibility contribution — see <this page>

The full import plan accompanies this page as `import_plan.md`.

## Licence

OSM data is ODbL 1.0 and everything derived from it stays ODbL. That is why no OSM-derived row is
ever sent to a destination that cannot carry the share-alike obligation; the redistribution matrix
enforces it, and a test proves `odbl` never reaches a Licence Ouverte partner.

## Contact

Sébastien Billion — contact@letmegetin.org
