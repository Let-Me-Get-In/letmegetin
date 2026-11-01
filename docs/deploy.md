# Deployment

The production stack is **Caddy + web + API + PostGIS + Redis**. Only Caddy publishes ports
(80/443); the API and web listen on the internal network. Metrics are internal only.

Secrets come from **Infisical**; the repository never holds a production `.env`.

## Secrets — Infisical

1. Install the [Infisical CLI](https://infisical.com/docs/cli/overview) on the host.
2. Create a **machine identity** (Universal Auth), add it to the project with read access, and
   create a client secret.
3. Create the bootstrap file (only the identity lives there):

   ```bash
   sudo install -d -m 700 /etc/letmegetin
   sudo cp deploy/infisical.env.example /etc/letmegetin/infisical.env
   sudo chmod 600 /etc/letmegetin/infisical.env
   # fill INFISICAL_PROJECT_ID, INFISICAL_DOMAIN (EU/self-hosted), CLIENT_ID, CLIENT_SECRET
   ```

4. Put the application secrets in the project's **prod** environment, path `/`:

   `APP_DOMAIN`, `API_DOMAIN`, `ACME_EMAIL`,
   `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `LETMEGETIN_JWT_SECRET`,
   `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `R2_BUCKET`, `R2_PREFIX`,
   `R2_JURISDICTION` (optional), `LETMEGETIN_SMTP_*`, `LETMEGETIN_SENTRY_DSN`,
   `NEXT_PUBLIC_SENTRY_DSN`, `ALERT_WEBHOOK`, `API_KEY` (leave empty for the web), `GIT_SHA`.

5. Every production command goes through the wrapper:

   ```bash
   ./scripts/with-secrets.sh <command>
   ```

   It logs in with the machine identity (or uses `INFISICAL_TOKEN`) and runs
   `infisical run --projectId … --env prod --path / -- <command>`.

`deploy/.env.prod.example` is kept only as a **fallback/reference** if Infisical is unavailable;
it is not the production path.

## First deploy

```bash
export INFISICAL_DOMAIN=https://eu.infisical.com   # EU Cloud; omit for US Cloud

./scripts/with-secrets.sh docker compose -p letmegetin-prod \
  -f docker-compose.prod.yml up -d --build

./scripts/with-secrets.sh docker compose -p letmegetin-prod \
  -f docker-compose.prod.yml exec api python -m letmegetin.seed
```

- Web: `https://$APP_DOMAIN`
- API: `https://$API_DOMAIN` (`/health`, `/docs`, `/openapi.json`)
- `/metrics` is **not** routed publicly; Prometheus scrapes `api:8000` internally.
- Migrations run on API start (entrypoint).
- The compose project is `letmegetin-prod`; it never shares volumes with the dev PostGIS.

## Local TLS smoke test

Caddy can use its internal CA for `app.localhost` / `api.localhost`:

```bash
export APP_DOMAIN=app.localhost API_DOMAIN=api.localhost ACME_EMAIL=test@example.org
export CADDY_CONFIG=Caddyfile.local
export POSTGRES_PASSWORD=test REDIS_PASSWORD=test LETMEGETIN_JWT_SECRET=test

docker compose -p letmegetin-prod -f docker-compose.prod.yml up -d --build
curl -k --resolve app.localhost:443:127.0.0.1 https://app.localhost/
curl -k --resolve api.localhost:443:127.0.0.1 https://api.localhost/health
```

This bypasses Infisical for a throwaway local stack; never use the test values in production.

## Observability profile

```bash
./scripts/with-secrets.sh docker compose -p letmegetin-prod \
  -f docker-compose.prod.yml --profile observability up -d prometheus alertmanager
```

Prometheus scrapes `api:8000/metrics`; alerts cover API down, 5xx rate, 429 rate and Redis down.
`ALERT_WEBHOOK` must be set before starting Alertmanager.

## Required secret names (Infisical, env `prod`)

| Variable | Purpose |
|---|---|
| `APP_DOMAIN`, `API_DOMAIN`, `ACME_EMAIL` | Caddy TLS |
| `POSTGRES_PASSWORD`, `REDIS_PASSWORD` | internal services |
| `LETMEGETIN_JWT_SECRET` | **required**, long random string |
| `LETMEGETIN_ENVIRONMENT` | `production` |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `R2_BUCKET`, `R2_PREFIX` | offsite R2 backups |
| `LETMEGETIN_SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN` | optional error tracking |
| `LETMEGETIN_SMTP_*` | verification emails (otherwise logged) |
| `ALERT_WEBHOOK` | Alertmanager receiver (observability profile) |
| `API_KEY` | leave empty for the public web; partner keys are server-side |

## Operations

- Backups/restore: `./scripts/with-secrets.sh ./scripts/backup.sh` (R2 via Wrangler),
  `./scripts/with-secrets.sh ./scripts/restore.sh <archive>`.
- Retention: `./scripts/with-secrets.sh docker compose … exec api letmegetin-admin retention`.
- Systemd timers read `/etc/letmegetin/infisical.env`; see `deploy/systemd/`.
- Runbook: [runbook.md](runbook.md).
- Changing a secret in Infisical requires **restarting the affected containers**; `infisical run`
  injects at process start.
