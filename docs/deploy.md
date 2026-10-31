# Deployment

## Local stack

```bash
export LETMEGETIN_JWT_SECRET="$(openssl rand -hex 32)"
docker compose -p letmegetin-prod -f docker-compose.prod.yml up --build
```

- API: http://localhost:8000 (`/health`, `/docs`)
- Web: http://localhost:3000
- PostGIS and Redis are internal; migrations run on API start.

Seed the fresh database once:

```bash
docker compose -p letmegetin-prod -f docker-compose.prod.yml exec api python -m letmegetin.seed
```

The compose project is named `letmegetin-prod` so it never shares containers or volumes with
the dev PostGIS (`letmegetin-db` on port 55433).

## Images

```bash
docker build -f docker/Dockerfile --target api -t letmegetin-api .
docker build -f docker/Dockerfile --target web -t letmegetin-web .
```

The API image runs `alembic upgrade head` then uvicorn. The web image is a Next standalone build.

## Required settings (API)

| Variable | Purpose |
|---|---|
| `LETMEGETIN_DATABASE_URL` | `postgresql+asyncpg://…` (PostGIS) |
| `LETMEGETIN_REDIS_URL` | `redis://redis:6379/0` for limits + cache |
| `LETMEGETIN_JWT_SECRET` | **required**, long random string |
| `LETMEGETIN_SMTP_*` | verification emails (otherwise logged) |

Web: `API_URL` (server-side), optional `API_KEY` for a partner key, and the
`NEXT_PUBLIC_MAP_TILE_*` pair.

## Operations

- `/health` is database-free; compose uses it for the API healthcheck.
- Redis is used for rate limits and the referential cache; if it is down the API falls back to
  in-process limits and skips the cache.
## Production checklist (before a real host)

- [ ] `LETMEGETIN_ENVIRONMENT=production` and a long random `LETMEGETIN_JWT_SECRET` (the API
      refuses to start with the development secret).
- [ ] TLS termination in front of the API and web (Caddy/Traefik/Cloudflare).
- [ ] Postgres and Redis backups, with a restore test.
- [ ] Monitoring on `/health`, the 429 rate and Redis availability.
- [ ] SMTP configured, or verification links only appear in the logs.
- [ ] A named tile provider via `NEXT_PUBLIC_MAP_TILE_URL`.
- [ ] A retention/purge job for `idempotency_key` and old `contribution` rows.
