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

Success responses carry:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1793400123
```

Over the limit: `429` with `Retry-After` (seconds). Limits are **sliding windows**; Redis is
shared across API workers, with an in-memory fallback (the budget is divided by the configured
worker count) if Redis is unavailable.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/places?lat&lng&radius&q&family&filters&limit` | Distance-sorted search |
| GET | `/places/candidates?lat&lng&name` | Duplicate prevention |
| GET | `/places/{slug}` | Record, tree, `filled_rate`, reviews summary, photos |
| GET | `/places/{slug}/reviews?page&size` | Paginated published reviews |
| GET | `/categories` | Categories |
| GET | `/categories/{slug}/criteria` | Criteria tree (ids included) |
| GET | `/categories/{slug}/grid` | Precomputed grid, `ETag`, `304` |
| GET | `/filters`, `/other-information` | Search filters, official labels |

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
