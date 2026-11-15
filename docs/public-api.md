# Public API v1

Base URL: `https://api.letmegetin.org/api/v1` (a local instance uses `http://localhost:8000`).
Interactive docs: `/docs`; machine schema: `/openapi.json`; generated schema in the repo: `docs/openapi.json`.

## Authentication

Public reads accept an optional **partner key**:

```bash
curl -H "X-API-Key: lmg_..." "https://api.letmegetin.org/api/v1/places?lat=48.85&lng=2.35"
```

- No key: the anonymous limit applies (60 requests/minute per IP by default).
- Valid key: the key's own limit applies.
- Invalid or revoked key: `401` with `WWW-Authenticate: ApiKey`.
- Writes (contribution, review) use a **bearer token**, not the API key.

Keys are created by the operator: `letmegetin-admin api-key create --label "Partner" --rpm 200`.
The raw key is printed once; only its SHA-256 hash is stored.

## Rate limits

Success responses and error responses carry:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1793400123
```

so a client that hits a `401` or a `422` still learns how much budget it has left.

Over the limit: `429` with `Retry-After` (seconds). Limits are **sliding windows**; Redis is
shared across API workers, with an in-memory fallback (the budget is divided by the configured
worker count) if Redis is unavailable. Behind Caddy the client IP is read from
`X-Forwarded-For`; the API itself is not publicly reachable.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/places?lat&lng&radius&q&family&category&filters&limit&offset&with_documentation` | Distance-sorted search, pageable; `with_documentation=true` adds each result's documentation |
| GET | `/places/candidates?lat&lng&name` | Duplicate prevention |
| GET | `/places/{slug}` | Record, tree, `filled_rate`, documentation ladder, reviews summary, photos, provenance |
| GET | `/places/{slug}/reviews?page&size` | Paginated published reviews |
| GET | `/categories` | Categories |
| GET | `/categories/{slug}/criteria` | Criteria tree (ids included) |
| GET | `/categories/{slug}/grid` | Precomputed grid, `ETag`, `304` |
| GET | `/filters`, `/other-information` | Search filters, official labels |
| GET | `/export/latest.json` | Current ODbL snapshot pointer, watermark, retention floor and available deltas |
| GET | `/export/{name}.zip` | One snapshot, delta or catch-up ODbL export archive |

The `category` value of `/places` is a slug from `GET /api/v1/categories`; an unknown slug is
`422`, like an unknown `family`.

Results are ordered by **distance ascending**, and ties are broken by **place id ascending**.
The order is therefore *total* and stable: two identical requests return the same places in the
same order, and a place never appears on two pages of the same paged search.

### Provenance

`GET /places/{slug}` is the only read endpoint that exposes provenance. It carries three
additive, optional fields — on the place itself and on every entry of `accessibility`:

| Field | Meaning |
|---|---|
| `source` | Where the copy came from (`acceslibre`, `user`, …) |
| `license` | The licence the row was written under (`lov2`, `odbl`, …), snapshotted at write time |
| `observed_at` | The source's own last-update claim, ISO 8601, nullable |

`observed_at` is what the source claims (Acceslibre `date_maj`), never our ingestion time: it is
**null** when the source makes no claim, and consumers must not read it as "last changed". The
ingestion timestamp (`retrieved_at`) stays internal and is not exposed. The search list
(`GET /places`) keeps its existing shape — no provenance per result.

### Documentation

`GET /places/{slug}` also says **how well documented a record is**, on a fixed six-rung ladder.
The level is a **stable enum**, not display text: a client maps the slug to its own localized copy,
prints `percent` verbatim, and never re-derives a level or restates the bounds.

| Level | Min % | Max % |
|---|---|---|
| none | 0 | 0 |
| sketch | 1 | 25 |
| partial | 26 | 50 |
| good | 51 | 75 |
| very_good | 76 | 99 |
| complete | 100 | 100 |

The same ladder is served, so it never has to be copied: `documentation_ladder` lists the six
rungs as `{slug, min, max}`, ascending.

| Field | Where | Shape |
|---|---|---|
| `documentation` | `GET /places/{slug}`; `GET /places` only with `with_documentation=true` | `{rate, percent, level}` for the whole record |
| `accessibility_by_family` | `GET /places/{slug}` | `{rate, percent, level}` per handicap family, same ladder and same grid-leaf denominator as the overall level |
| `documentation_ladder` | `GET /places/{slug}` | `[{slug, min, max}]`, the six rungs |

`rate` is the share of the category grid's answerable criteria that carry a recorded value, in
`[0, 1]`. `percent` is the integer the server used to pick `level`
(`floor(rate * 100 + 0.5)`, clamped to `[0, 100]`): print it as-is, because rounding it again can
make the printed percentage and the level disagree at a bound. A family with no criterion in the
place's category grid is **absent** from `accessibility_by_family`; that is "nothing to answer",
never `0 %`.

`GET /places` carries `documentation` only under `with_documentation=true`. Without the flag the key
is **absent** from each result — not `null` — so an existing consumer pays nothing, and the body
stays a bare JSON array either way.

**Breaking change.** `accessibility_by_family` used to map each family to a bare float rate; it now
maps to `{rate, percent, level}`. A consumer that read the float reads `.rate` of the new object.

### Pagination

`/places` returns at most **100** hits per request (`limit`, default 50). `offset` is the number
of hits to skip (default 0, maximum 10 000); `offset=100&limit=100` is the second page.

Whether another page exists is carried by the **`X-Has-More`** response header, `true` or
`false`, so a client never has to fetch an empty tail page. The response body stays a **bare
JSON array** — existing consumers keep working unchanged and can ignore both parameters.

```bash
curl -D - "https://api.letmegetin.org/api/v1/places?lat=48.85&lng=2.35&limit=100&offset=100"
# X-Has-More: false
```

Pages are consistent only while the underlying data does not change: a contribution or an
import between two requests can shift a place across a page boundary.

### Combining filters

`filters` takes a comma-separated list of criterion ids (from
`GET /api/v1/categories/{slug}/criteria`) and combines them with **AND**: a place is returned
only if it holds a value for **every** id, so each added id narrows the result set.

```bash
curl "https://api.letmegetin.org/api/v1/places?lat=48.85&lng=2.35&filters=12,34"
```

returns the places that hold both criterion 12 and criterion 34. Repeated ids are ignored.

**Behaviour change.** Before this release the ids were combined with **OR** (any matching value
qualified), so adding an id widened the results. A consumer that relied on the union must now
issue one request per criterion (or union the `slug` lists client-side); a consumer that wanted
the intersection now gets it from a single request. Parameter names and response shapes are
unchanged.

Writes: `POST /auth/register|login|refresh|logout|verify-email|resend-verification`,
`PUT /places/{slug}/accessibility/{criterion}` and `POST /places/{slug}/reviews` (bearer token,
verified email); `PATCH /reviews/{id}` (admin).

## ODbL export

The whole referential is also published as an ODbL export, independently of the JSON API. The
operator generates the archives on the host (`letmegetin-admin export odbl`); the API only reads
the export directory and serves what is there. Nothing is built per request and there is no
authentication beyond the normal anonymous quota (or a partner key's quota).

| Method | Path | Cache | Purpose |
|---|---|---|---|
| GET | `/export/latest.json` | `max-age=300` | Current snapshot pointer, delta watermark, retention floor and available deltas |
| GET | `/export/{name}.zip` | `max-age=3600` | One snapshot, delta or catch-up archive, `application/zip` |

A missing index, an unknown archive and an unusable name all answer `404` with the same body —
never `503` — so the routes are not an oracle for which files exist. `latest.json` is `404` until
the first export exists, including on a deployment whose export volume is not provisioned.

### What an archive holds

Every archive is UTF-8, comma-separated, RFC 4180 quoted, with a header row on every file and no
BOM. It has the same seven entries whether it is a snapshot or a delta:

| Entry | Content |
|---|---|
| `places.csv` | One row per canonical place, including places with no answer |
| `categories.csv` | The full category tree |
| `criteria.csv` | The full criterion tree |
| `answers.csv` | One winning answer per `(place_id, criterion_slug)` |
| `aliases.csv` | Merged place id → canonical place id (the tombstone stream) |
| `ATTRIBUTION.txt` | The sources this ZIP actually contains, plus the Produced Works notice |
| `manifest.json` | `schema_version`, `generated_at`, `referential_version`, per-file row counts, exclusion counters and `attribution_ref` |

A delta archive carries `mode`, `from_seq` and `to_seq` in its manifest; a snapshot carries none of
the three. Read `manifest.json` first and refuse a `schema_version` major you do not know
(currently `"1.0"`).

**Places.** Only canonical places are exported. A merged place never appears as a place: it appears
in `aliases.csv` as `alias_id → canonical_id`, and its answers are rewritten onto the canonical
place's id in `answers.csv`. A place is never dropped because one of its answers is withheld.

**Answers.** One winning answer per `(place_id, criterion_slug)`. When the canonical place itself
holds a value for that criterion, it wins; otherwise the newest recorded answer among the merged
places wins. An answer whose own licence (or whose canonical place's licence) does not allow
`open_export` is omitted, and the manifest counts it — a partner always knows what was withheld.

**Exclusions.** `excluded_places`, `excluded_answers` and `place_withheld_answers` are arrays of
`{source, licence, count}`, per `(source, licence)`: canonical places withheld at place level,
answers withheld or displaced by the winner rule, and answers absent because their canonical place
is withheld. The counters are part of the contract, not diagnostics: they are how a partial place
stays auditable.

**Dates.** `date` is the source's own last-update claim (`observed_at`) when it declares one,
otherwise our retrieval time for a place / recording time for an answer. `manifest.generated_at` is
when the archive was produced, and `referential_version` identifies the referential state it holds.

### Columns and origin ids

```text
places.csv:      place_id,origin_id,slug,name,category_slug,source_category,address_full,city,postal_code,country_code,lat,lng,operating_status,website,phone,source,source_license,source_url,date
categories.csv:  category_id,slug,parent_id,parent_slug,name,label
criteria.csv:    criterion_id,slug,parent_id,parent_slug,type,position,handicap_families,label,en17210_ref
answers.csv:     place_id,criterion_slug,value,source,source_license,source_url,date
aliases.csv:     alias_id,canonical_id
```

`label` (`{fr, en}`), `value` (the recorded answer object) and `handicap_families` (a list) are
JSON text. `source_license` is the licence slug (`lov2`, `odbl`, `cdla`, `dual`); `source_url` may be
empty. `category_slug` and `criterion_slug` join to the `slug` in the referential files — do not
join answers on the internal criterion id.

The `*_id` columns are our surrogate ids. They are stable within one archive and useful for joins
inside it, but they are **not** the origin identity. Per file, the origin id is:

| File | Origin id |
|---|---|
| `places.csv` | the pair `(source, origin_id)` — `origin_id` is the source's own id |
| `answers.csv` | the natural key `(place_id, criterion_slug)` — answers have no source-side surrogate id |
| `categories.csv`, `criteria.csv` | the `slug` |

### Delta contract

`latest.json` is the index. It always carries the snapshot, the watermark, the retention floor and
the delta chain as **separate** fields:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-11-14T10:15:00.123456Z",
  "referential_version": 42,
  "snapshot": {"name": "export-20261114T101500123456Z-full.zip", "seq": 900},
  "watermark": 940,
  "retention_floor_seq": 800,
  "deltas": [
    {"name": "delta-20261115T101500123456Z.zip", "from_seq": 900, "to_seq": 920},
    {"name": "delta-20261116T101500123456Z.zip", "from_seq": 920, "to_seq": 940}
  ],
  "attribution_ref": "ATTRIBUTION.txt"
}
```

- `snapshot {name, seq}` — the last full snapshot and its boundary. Download that archive first.
- `watermark` — the highest event sequence published in a delta; later rows are not published yet.
- `retention_floor_seq` — the oldest replayable boundary; a catch-up below it is refused.
- `deltas[]` — the deltas published since that snapshot, each `{name, from_seq, to_seq}`.

The delta boundary is PostgreSQL's **MVCC boundary**, not a row count. A delta contains exactly the
events `watermark < seq <= safe_seq()`, where `safe_seq()` is the highest event whose inserting
transaction had already committed when the run started. `safe_seq()` is read as the first statement
of the same `REPEATABLE READ` transaction that streams the rows, so the boundary and the streamed
rows agree by construction. An event from a transaction still in flight is excluded and picked up
by a later delta — never lost, never duplicated.

Apply the archives **in order**: the snapshot, then each delta in `deltas[]` order. Each delta's
`from_seq` equals the previous delta's `to_seq` (the first starts at `snapshot.seq`), and each
archive repeats `from_seq`/`to_seq` in its own `manifest.json`, so a partner can verify contiguity
before applying. Every event is a full row state keyed by id, so applying the same delta twice is
harmless (idempotent upsert). A delta is one window, never "cumulative since the snapshot"; the
windows are the chain.

A delta archive contains the same seven entries: `categories.csv` and `criteria.csv` are always
complete (the referential is small and versioned), while `places.csv`, `answers.csv` and
`aliases.csv` hold only the rows whose events fall in the window. Nothing is ever deleted from the
data; merges are the tombstone stream in `aliases.csv`, so there is no deletion file.

The watermark moves only after the delta archive is completely written and fsynced. A failed run
leaves it untouched, so the next run re-emits the same window. A new snapshot starts a new chain:
`deltas` becomes empty, `watermark` equals the new snapshot's `seq`, and `retention_floor_seq`
becomes the previous snapshot's `seq` (the first snapshot uses its own).

**Catch-up.** `letmegetin-admin export odbl --since <seq>` (or `--since <ISO date>`) writes a
cumulative catch-up archive for a partner who lost a delta. It leaves `latest.json` untouched. It
is refused when the boundary resolves below `retention_floor_seq`; the error names the floor and
the snapshot to restart from. `--since <date>` resolves to the last event of that ISO day, in
server time.

### CSV formula guard

A cell is guarded only when it is a **free-text** column and starts with `=`, `+`, `-` or `@`; the
writer then prefixes a single `'` so a spreadsheet cannot run it as a formula. The allow-list is
fixed per file:

| File | Guarded columns |
|---|---|
| `places.csv` | `name`, `address_full`, `city`, `source_category` |
| `categories.csv` | `name`, `label` |
| `criteria.csv` | `label` |

The header row is never guarded, and no numeric, id, date, count or JSON column is guarded:
`lat`, `lng`, `phone`, `postal_code`, ids, dates, `value` and `handicap_families` reach the partner
unchanged. A negative longitude or a `+` phone number therefore stays intact, while a formula typed
into a name or an address is neutralised. `label` is JSON (`{"fr": …}`), so it cannot begin with a
formula character and the guard never changes it in practice.

### Attribution and licence

`ATTRIBUTION.txt` is inside every ZIP and repeated verbatim in `manifest.attribution`. It lists
**only the sources present in that ZIP** — a source is present when at least one of its rows is
exported. A source whose rows are all withheld is not listed, so the notice never claims data the
archive does not contain. For each present source it carries the legal name and licence from
`data/referential/licences.csv`, the last-update date of the data held, and the licence's reviewed
`attribution_text` sentence — the wording the licence requires, not a generic placeholder. There
is no per-row attribution column: the text belongs in one place, not on 1.7M answer rows.

There is no OpenStreetMap or Overture line today: upstream sources appear the day their rows do.
Nothing is hard-coded and no partner name is invented.

The API and the map are Produced Works under the ODbL (attribution only, no share-alike obligation on them).

Later exports may include sources not listed in this one.

### lov2 partner feed

The same archive is also produced for a **lov2** destination
(`letmegetin-admin export odbl --destination lov2_partner --out <dir>`). It is not served by the
API: like any non-ODbL export it is written to the directory the operator names, so
`/export/{name}.zip` never resolves to it.

The partner feed is the Phase 14 export with the licence predicate at `lov2_partner`: exactly the
rows the reviewed destination matrix allows there, full snapshots only (no delta chain). It carries
the same seven entries, the same `manifest.json` and the same `latest.json`, with **partner keys**
instead of ours:

| Entry | Key column |
|---|---|
| `places.csv` | `identifier` (AccesLibre's ERP slug, else its `origin_id`) and `activite` (its category value) |
| `categories.csv` | `activite` (the canonical value of the category, its largest population) |
| `criteria.csv` | `field` (one of AccesLibre's 8 writable field names) |
| `answers.csv` | `field` — the answer's value only, never a user id |
| `aliases.csv` | `alias_id`, `canonical_id`, both partner identifiers |

No column is named `slug`, `category_slug` or `criterion_slug`: our vocabulary never reaches the
feed. A place, category or answer we cannot express in AccesLibre's vocabulary is **not** dropped
silently: it lands in `mapping.csv`, written next to the archive (never inside it), with one row per
`entity;identifier;reason;detail`. That sidecar merges the reviewed document
`data/referential/acceslibre_mapping.csv` (every criterion outside the 8 field names, and the
canonical `activite` chosen per category) with whatever this run could not key.

If the identifier rule recorded by `letmegetin-admin acceslibre probe` is still `blocked`, every
place diverts to the mapping document and `places.csv` is header-only — the feed never keys on an
unverified identifier.

## Idempotency

Write endpoints accept an `Idempotency-Key` header (max 128 characters):

- `PUT /places/{slug}/accessibility/{criterion}`
- `POST /places/{slug}/reviews`

The same key with the same payload replays the stored response (200/201) instead of repeating the
write. The same key with a different payload returns `409`. Keys are scoped to the authenticated
user; operators purge rows older than 24 hours.

`PUT .../accessibility/...` is also idempotent without a key: repeating an unchanged value does not
append a contribution row. `POST /auth/logout` is idempotent (204 even without a session);
`POST /auth/refresh` is intentionally **not** idempotent (rotation and replay protection), and
`POST /auth/register` returns 409 for an existing email.

## Errors

`{"detail": "..."}`, with `401` (authentication), `403` (role/email verification), `404`,
`409` (duplicate email), `422` (validation), `429` (quota).

## Versioning and licence

The path is versioned (`/api/v1`). Breaking changes go to `/api/v2`. The referential is open data.
Attribution and share-alike obligations for a given archive are those of the licences listed in its
`ATTRIBUTION.txt`; the [ODbL export](#odbl-export) section above is the contract for the export,
and it lists only the sources a ZIP actually contains.
