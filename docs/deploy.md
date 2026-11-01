# Deployment

The production stack is **Caddy + web + API + PostGIS + Redis**. Only Caddy publishes ports
(80/443); the API and web listen on the internal network. Metrics are internal only.

## First deploy

```bash
cp deploy/.env.prod.example deploy/.env.prod
# fill APP_DOMAIN, API_DOMAIN, ACME_EMAIL, POSTGRES_PASSWORD, REDIS_PASSWORD,
# LETMEGETIN_JWT_SECRET (openssl rand -hex 32), SMTP, Sentry DSNs

docker compose -p letmegetin-prod --env-file deploy/.env.prod -f docker-compose.prod.yml up -d --build
docker compose -p letmegetin-prod --env-file deploy/.env.prod -f docker-compose.prod.yml \
  exec api python -m letmegetin.seed
```

- Web: `https://$APP_DOMAIN`
- API: `https://$API_DOMAIN` (`/health`, `/docs`, `/openapi.json`)
- `/metrics` is **not** routed publicly; Prometheus scrapes `api:8000` internally.
- Migrations run on API start (entrypoint).
- The compose project is `letmegetin-prod`; it never shares volumes with the dev PostGIS
  (`letmegetin-db` on 55433).

## Local TLS smoke test

Caddy can use its internal CA for `app.localhost` / `api.localhost`:

```bash
export POSTGRES_PASSWORD=test REDIS_PASSWORD=test LETMEGETIN_JWT_SECRET=test
export APP_DOMAIN=app.localhost API_DOMAIN=api.localhost ACME_EMAIL=test@example.org
export CADDY_CONFIG=Caddyfile.local
docker compose -p letmegetin-prod -f docker-compose.prod.yml up -d --build

curl -k --resolve app.localhost:443:127.0.0.1 https://app.localhost/
curl -k --resolve api.localhost:443:127.0.0.1 https://api.localhost/health
curl -k --resolve api.localhost:443:127.0.0.1 -o /dev/null -w '%{http_code}\n' \
  https://api.localhost/metrics   # 404: blocked by Caddy
```

## Observability profile

```bash
docker compose -p letmegetin-prod --env-file deploy/.env.prod -f docker-compose.prod.yml \
  --profile observability up -d prometheus alertmanager
```

Prometheus scrapes `api:8000/metrics`; the alert rules cover API down, 5xx rate, 429 rate and
Redis down. Alertmanager forwards to `ALERT_WEBHOOK`.

## Required API settings

| Variable | Purpose |
|---|---|
| `LETMEGETIN_ENVIRONMENT` | `production` (required to enforce the secret guard) |
| `LETMEGETIN_DATABASE_URL` | `postgresql+asyncpg://…` (PostGIS) |
| `LETMEGETIN_REDIS_URL` | `redis://:password@redis:6379/0` |
| `LETMEGETIN_JWT_SECRET` | **required**, long random string |
| `LETMEGETIN_SENTRY_DSN` | optional; no DSN → Sentry disabled |
| `LETMEGETIN_SMTP_*` | verification emails (otherwise logged) |
| `LETMEGETIN_GIT_SHA` | Sentry release |

Web (build-time): `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_MAP_TILE_URL`,
`NEXT_PUBLIC_MAP_ATTRIBUTION`. Runtime: `API_URL`; leave `API_KEY` empty for the public web so
each visitor keeps their own per-IP limit (the BFF forwards `X-Forwarded-For`).

## Operations

- Backups/restore: `scripts/backup.sh` (Cloudflare R2 offsite via `R2_*`, generic S3 supported),
  `scripts/restore.sh`, systemd units in `deploy/systemd/`.
- Retention: `letmegetin-admin retention [--dry-run]`, daily timer.
- Runbook: [runbook.md](runbook.md).
- `/health` is database-free; the API healthcheck uses it.
- Redis is used for limits and the cache; if it is down the API falls back to in-process limits
  and skips the cache.
