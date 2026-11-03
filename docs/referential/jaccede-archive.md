# Jaccede and the Internet Archive

**Status:** investigated 2026-11-03. **Conclusion: the archive does not replace
the reconstructed seed.** The API payloads — the only place the real referential
ever lived — are not archived; only HTTP 403 errors are.

This note records what was checked, so nobody repeats the search hoping for a
data dump that is not there.

## What Jaccede was

`jaccede.com`, the collaborative guide to accessible places, operated by the
association Jaccede. The site is indexed by the Wayback Machine from
**25 May 2002 to 24 Oct 2026** with **771 captures**; the product itself was live
until **December 2024**. By January 2025 the domain served a single page —
*« Jaccede fait une pause pour se réinventer »* — and nothing else.

The capture most people land on
(`web.archive.org/web/20250107144223/https://jaccede.com/`) is that shutdown
page. It contains no product data.

## The product was a single-page application

The last frontend (2022-2024) is a React SPA: the archived HTML carries only the
shell and the navigation. Everything else was fetched client-side from
`api.jaccede.com/v4/`. The endpoints seen in the archive are exactly the
referential we had to reconstruct:

```
/v4/categories?lang=fr              categories
/v4/accessibility_filters?lang=fr   accessibility criteria
/v4/places/<slug>?lang=fr           place records
/v4/pages?lang=fr&simple=true       editorial pages
/v4/challenges?lang=fr              gamification
```

**Every archived response of those endpoints is HTTP 403.** Cloudflare blocked
the archiver, so the Wayback Machine stored the rejection, not the JSON. The only
`200` anywhere on `api.jaccede.com` is a 2013 `/v2/docs` returning
`{"status":"NOK","results":{"error_message":"Unknown resource"}}`.

There is therefore **no recoverable dump** of categories, criteria or places.

## What is recoverable

| Asset | Where | Use |
|---|---|---|
| Category slugs | `www.jaccede.com/static/js/<slug>.png` and `<slug>_off.png` (2022 assets: `airport`, `bakery`, `bank`, `aquarium`, `amusement_park`, `art_gallery`, `atm`, …) | Cross-check our 158 category slugs |
| Place slugs | archived `/v4/places/<slug>` URLs (`0kd-fromagerie-angers`, `0tf-pizza-guillou-nice`, …) | Measure our Acceslibre import coverage against theirs |
| Pre-2016 place pages | `/accessible-places/` was **server-rendered** until ~2016 | The only place criteria labels might appear as HTML |

The pre-2016 pages are the one lead worth chasing: before the SPA, a place page
was HTML, so the criteria tree may be readable in text. Caveat — that would be
the **v1 grid of 2012-2015**, which is not necessarily the grid in use in 2024.

## Place identity

Archived place URLs use Google Place IDs (`ChIJ…`) as the identifier. Jaccede
therefore keyed its places on Google, which we cannot do (Google Places ToS
forbids storing the data). Our `(source, source_id)` + `place_alias` soft-dedup
model is the replacement, and it is not a downgrade: it never blocks ingestion on
a third party.

## Retrying the pre-2016 pages

The Wayback CDX API was returning *"Temporarily Offline"* during this
investigation — retry later, in this order:

```bash
# 1. list candidate place pages (server-rendered era)
curl "https://web.archive.org/cdx/search/cdx?url=www.jaccede.com/accessible-places/*&output=json&from=2012&to=2016&collapse=urlkey&limit=50"

# 2. open one capture as raw HTML and look for criterion labels
curl "https://web.archive.org/web/<timestamp>id_/http://www.jaccede.com/accessible-places/<path>/"
```

If labels come out, they enrich `data/referential/criteria.json` as **aliases**;
they do not change our structure.

## Consequence for this repository

Nothing in the plan changes. `data/referential/` stays the source of truth: the
category-1 grid as universal base, extended and editable. The archive is a
cross-check for slugs and coverage, not a source of records.
