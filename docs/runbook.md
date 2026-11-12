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
./scripts/with-secrets.sh ./scripts/backup.sh
```

- Writes `backups/<UTC timestamp>.tar.gz` (Postgres custom dump + Redis RDB) and a `.sha256`.
- Keeps the last 7 local archives.
- **Offsite (Cloudflare R2)**: the script reads `cf_backup_access_key_id`,
  `cf_backup_secret_access_key`, `cf_account_id` and `cf_backup_bucket` first, then falls back to
  `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT` and `R2_BUCKET`; `R2_PREFIX` defaults to
  `letmegetin` and `R2_JURISDICTION=eu` is optional. The upload is a signed S3 `PUT` made by **curl**
  (`--aws-sigv4`): no AWS CLI, no Wrangler, no Node image. Without a bucket it warns and stays local.
  The checksum file names the archive by bare filename, so `sha256sum -c` works on a download.

### Cloudflare R2 setup

1. Create the bucket (in production: `lmgi-backups`).
2. **R2 → Manage R2 API Tokens → Create API token**, permission **Object Read & Write**, scoped to
   that bucket only. The screen returns an **Access Key ID** and a **Secret Access Key**. Note the
   account ID from the dashboard.
3. Store `cf_backup_access_key_id`, `cf_backup_secret_access_key`, `cf_account_id` and
   `cf_backup_bucket` in Infisical (`prod`, path `/`).
4. **Lifecycle**: bucket → Settings → Object lifecycle → delete after 30 days (or transition to
   Infrequent Access after 7 days, delete after 90). The script does not delete remote objects.
5. EU jurisdiction: set `R2_JURISDICTION=eu` (endpoint becomes `<account>.eu.r2.cloudflarestorage.com`).
6. R2 has no egress fees; keep the key pair bucket-scoped and rotate it like any secret.

   Why a key pair and not a Cloudflare API token: the token screen only offers `Workers R2 Storage`
   at **account** scope, which would let a nightly cron rewrite `lmgi-tfstate`. The R2 screen is the
   only one that scopes a credential to a single bucket.
- Installed as `deploy/systemd/letmegetin-backup.{service,timer}` (daily 02:00). The unit reads
  `/etc/letmegetin/infisical.env` and runs the wrapper, so no application secret sits on disk.

## Restore (tested path)

```bash
./scripts/with-secrets.sh ./scripts/restore.sh backups/<timestamp>.tar.gz
```

Download from R2 first (the wrapper injects the R2/Cloudflare secrets):

```bash
./scripts/with-secrets.sh bash -c '
  ep="https://$cf_account_id.r2.cloudflarestorage.com/$cf_backup_bucket/letmegetin"
  for f in <timestamp>.tar.gz <timestamp>.tar.gz.sha256; do
    curl -fsS --aws-sigv4 "aws:amz:auto:s3" \
      --user "$cf_backup_access_key_id:$cf_backup_secret_access_key" \
      "$ep/$f" -o "backups/$f"
  done'
sha256sum -c backups/<timestamp>.tar.gz.sha256
```

Then restore into **`letmegetin_restore`**, never the live DB.
- Prints the row counts of `place`, `categories`, `review`, `users`.
- Inspect the scratch DB; then promote deliberately:
  ```bash
  ./scripts/with-secrets.sh ./scripts/restore.sh backups/<timestamp>.tar.gz --promote
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

- Application secrets live in **Infisical** (project, environment `prod`, path `/`). The server
  holds only `/etc/letmegetin/infisical.env` (machine identity, mode 600).
- `./scripts/with-secrets.sh <command>` authenticates and injects secrets; systemd timers use the
  same wrapper.
- Rotate `LETMEGETIN_JWT_SECRET` in Infisical and restart the API (all sessions invalidated).
- Rotate Postgres/Redis/R2/SMTP secrets in Infisical and restart the affected services;
  `infisical run` injects at process start, so a running container keeps the old value.
- Rotate the machine identity client secret in Infisical and `/etc/letmegetin/infisical.env`;
  timers log in on each run.
- `deploy/.env.prod` is a fallback only; do not use it on the production host.
