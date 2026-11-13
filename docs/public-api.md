# Public API v1

Base URL: `https://api.letmegetin.org/api/v1` (a local instance uses `http://localhost:8000`).
Interactive docs: `/docs`; machine schema: `/openapi.json`; this file: `docs/openapi.json`.

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

The path is versioned (`/api/v1`). Breaking changes go to `/api/v2`. The referential is open data
(Acceslibre Etalab 2.0, OpenStreetMap ODbL, Overture CDLA); attribution is required and the ODbL
share-alike applies to derived databases.
