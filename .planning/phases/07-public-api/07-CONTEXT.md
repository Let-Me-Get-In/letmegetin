# Phase 7: Public API & Deployment — Context

**Gathered:** 2026-10-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Open the API to partners and make the stack deployable:

- **API keys** for partner calls, with per-key rate limits and clear headers.
- **OpenAPI** served, documented and checked in CI.
- **Deployment**: production images (API + web) and a compose stack that runs migrations and is
  reachable locally.

Out of scope: billing, self-service key portal, OAuth, multi-region, a real cloud account.
</domain>

<decisions>
## Decisions

- **Keys are optional on public reads.** Anonymous callers keep a modest IP limit (the web BFF
  still works); a valid `X-API-Key` gets its own `rpm`. An invalid key is **401**, never silently
  anonymous.
- **Key format** `lmg_<random>`; only a **SHA-256 hash** is stored. The raw key is printed once by
  the admin CLI. `api_key(id, label, key_hash unique, rpm, active, created)`.
- **No write path over HTTP** for keys: the operator CLI (`letmegetin.admin api-key`) creates,
  lists and revokes them, like the rest of the referential.
- **Rate limiting is a fixed window in Redis** (`INCR` + `EXPIRE` in one Lua script), keyed by
  key id or client IP. Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`;
  `429` with `Retry-After`. If Redis is unreachable, fall back to the in-memory limiter so the API
  stays up.
- **Redis also serves the cache**: the referential reads (categories, criteria trees, precomputed
  grids) are cached under the current `referential_version`, so an admin edit naturally
  invalidates them. Place data is **not** cached (contributions/reviews must be fresh). Without
  `LETMEGETIN_REDIS_URL`, the cache is a no-op and the limiter uses memory.
- **Two limit classes**: public reads (default 60 rpm/IP, key `rpm` if provided) and auth
  endpoints (10 rpm/IP) to slow credential stuffing.
- **No CORS for partners**: they call server-side. The web app uses its own BFF, which can send an
  `API_KEY` server-side.
- **OpenAPI is a deliverable**: a title/description/tags, the `X-API-Key` security scheme,
  `/docs` and `/openapi.json`; a generated `docs/openapi.json` is checked in and compared in CI.
- **Deployment is local-first**: a multi-stage Dockerfile (`api`, `web`), a compose stack with
  PostGIS + **Redis** + API + web, migrations on API start and healthchecks. A real host needs
  credentials and stays a follow-up.
- **New dependencies**: `redis` (async client) in production; the dev/CI stack adds a Redis
  service. `fakeredis` is the test double.
</decisions>

<canonical_refs>
- `.planning/REQUIREMENTS.md` — API-01, API-02.
- `.planning/ROADMAP.md` — Phase 7 success criteria.
- `.planning/phases/03-places-search/03-CONTEXT.md` — public read API and grids.
- `.planning/phases/05-auth-contribution/05-CONTEXT.md` — auth endpoints.
- `docs/` — public API documentation (to create).
</canonical_refs>

<code_context>
- `main.py` builds a bare `FastAPI(title, version)`; `/docs` and `/openapi.json` already exist by
  default.
- `api/v1/router.py` includes `auth`, `referential`, `places`; all public reads are unauthenticated.
- `admin.py` is a Typer app with category/criterion/vocabulary/labels/import groups.
- `docker-compose.yml` currently runs PostGIS only; there is no Redis, API or web image.
- `web/` is a Next 16 app; the BFF proxies `/api/*` to `API_URL`.
- The suite is 166 backend + 24 web tests; coverage floor 85 %.
</code_context>

<deferred>
- Billing and key self-service, OAuth, Redis-backed limits, multi-region, CDN, real cloud deploy.
</deferred>

---
*Phase: 07-public-api*
