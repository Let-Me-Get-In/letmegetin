# Runbook

Operational procedures for the LetMeGetIn production stack (Caddy, web, API, PostGIS, Redis).

## Deploy

1. `git pull` on the host, then rebuild:
   ```bash
   docker compose -p letmegetin-prod --env-file deploy/.env.prod -f docker-compose.prod.yml up -d --build
   ```
2. Watch the API health: `curl -fsS https://$API_DOMAIN/health`.
3. Check the web: `curl -fsS -o /dev/null -w '%{http_code}' https://$APP_DOMAIN/`.
4. First deploy only: seed with
   `docker compose ... exec api python -m letmegetin.seed`.
5. Migrations are applied by the API entrypoint; a failed migration keeps the old container
   running (compose does not replace it until healthy).

## Rollback

- **Code**: redeploy the previous image/commit (`git checkout <sha>` + `up -d --build`). Migrations
  are forward-only; read the release notes before rolling back a schema change.
- **Data**: restore a backup (below); data loss is bounded by the last backup.

## Backup

```bash
POSTGRES_PASSWORD=... REDIS_PASSWORD=... ./scripts/backup.sh
```

- Writes `backups/<UTC timestamp>.tar.gz` (Postgres custom dump + Redis RDB) and a `.sha256`.
- Keeps the last 7 local archives.
- **Offsite (Cloudflare R2)**: set `R2_ACCOUNT_ID`, `R2_BUCKET`, `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY` (and `S3_PREFIX`, default `letmegetin`). The script derives
  `https://<account>.r2.cloudflarestorage.com` and uploads the archive and its checksum through the
  AWS CLI container. Without `R2_BUCKET`/`S3_BUCKET` it warns and stays local. Generic S3 is still
  supported through `S3_BUCKET` + `AWS_*`.

### Cloudflare R2 setup

1. Create the bucket `letmegetin-backups` (EU jurisdiction if required).
2. **Manage R2 API Tokens** → create a token with **Object Read & Write**, scoped to that bucket.
3. Put the Access Key ID / Secret Access Key and the account ID in `deploy/.env.prod`.
4. **Lifecycle**: bucket → Settings → Object lifecycle → delete after 30 days (or transition to
   Infrequent Access after 7 days, delete after 90). The script does not delete remote objects.
5. EU jurisdiction: set
   `S3_ENDPOINT_URL=https://<account>.eu.r2.cloudflarestorage.com`; otherwise it is derived.
6. R2 has no egress fees; keep the token bucket-scoped and rotate it like any secret.
- Installed as `deploy/systemd/letmegetin-backup.{service,timer}` (daily 02:00, `EnvironmentFile`
  points at `deploy/.env.prod`).

## Restore (tested path)

```bash
POSTGRES_PASSWORD=... ./scripts/restore.sh backups/<timestamp>.tar.gz
```

Download from R2 first (same env as the backup):

```bash
docker run --rm -v "$PWD/backups:/out" \
  -e AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" \
  amazon/aws-cli --endpoint-url "https://$R2_ACCOUNT_ID.r2.cloudflarestorage.com" \
  s3 cp "s3://$R2_BUCKET/$S3_PREFIX/<timestamp>.tar.gz" /out/
sha256sum -c backups/<timestamp>.tar.gz.sha256
```

Then restore into **`letmegetin_restore`**, never the live DB.
- Prints the row counts of `place`, `categories`, `review`, `users`.
- Inspect the scratch DB; then promote deliberately:
  ```bash
  POSTGRES_PASSWORD=... ./scripts/restore.sh backups/<timestamp>.tar.gz --promote
  ```
  Promotion stops the API, replaces the database and restarts the API. Verify `/health` before
  reopening traffic.

### Restore test (quarterly)

Create a marker, back up, delete the marker, restore the scratch DB, verify the marker is back.
Never promote during the drill.

## TLS

- Caddy obtains and renews certificates automatically. Check `docker compose logs caddy` for ACME
  errors.
- Do not expose the API or web ports; only Caddy publishes 80/443.
- HSTS is set by Caddy; keep the domains HTTPS-only.

## Monitoring and errors

- Prometheus (profile `observability`) scrapes `api:8000/metrics`.
- Alerts: API down, 5xx rate, 429 rate, Redis down → Alertmanager → `ALERT_WEBHOOK`.
  **Set `ALERT_WEBHOOK` before starting the observability profile**; Alertmanager will not load with
  an empty URL.
- Sentry captures API and web exceptions (no request bodies, no PII; emails redacted). Without a
  DSN it is disabled; the API logs a production warning when `LETMEGETIN_SENTRY_DSN` is missing.
- Useful signals: `letmegetin_http_requests_total`, `letmegetin_rate_limited_total`,
  `letmegetin_redis_up`, `/health`, Caddy logs.

## Retention

```bash
docker compose ... exec api letmegetin-admin retention --dry-run
docker compose ... exec api letmegetin-admin retention
```

- Deletes idempotency keys older than 24 h and expired/revoked refresh tokens older than 30 days.
- Never deletes contributions or reviews.
- Installed as `deploy/systemd/letmegetin-retention.{service,timer}` (daily 03:00).

## Incident checklist

1. Is the API up? `/health`, `docker compose ps`, API logs.
2. Are 5xx or 429 spikes visible in Prometheus/Sentry?
3. Is Redis up? If not, limits fall back per worker and the cache is skipped; restore Redis first.
4. Is the database reachable/backed up? Check disk and `pg_isready`.
5. If data is corrupted: restore the last backup into a scratch DB, verify, then promote.

## Secrets

- `deploy/.env.prod` is git-ignored and owned by the deploy user (mode 600).
- Rotate `LETMEGETIN_JWT_SECRET` by restarting the API (all sessions invalidated).
- Rotate Postgres/Redis passwords with a maintenance window; update `deploy/.env.prod` and restart
  the dependent services.
