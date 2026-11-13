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

### Restore drill (daily, automated)

`letmegetin-restore-drill.timer` runs the drill every day at 04:00 UTC, after the 02:00 backup
and the 03:00 retention. It is the only test of the copy that actually left the machine:

1. Lists `lmgi-backups` over the S3 API (the same `curl --aws-sigv4` signing the backup uses),
   and takes the newest archive.
2. Downloads that archive and its `.sha256`, and verifies the checksum against the downloaded
   bytes. The local `backups/` directory is never the source.
3. Restores into **`letmegetin_restore`**, in the development stack — never production, and no
   promote path.
4. Asserts the restored copy against `letmegetin_dev`: same `public` table count, same
   `alembic_version.version_num`, and `place`, `categories` and `place_accessibility` non-empty.
5. Drops the scratch database on success.

On failure the scratch database is **kept** for inspection, and the journal says so:
`drill failed (rc=<n>): scratch database kept as letmegetin_restore`. The next clean run drops
and recreates it, so nothing accumulates.

Two markers in the node_exporter textfile directory, both read by Prometheus:

| Marker | Written | Alert |
|---|---|---|
| `restore.prom` | on success only | `RestoreStale` — older than 8 days, or never written |
| `restore-failure.prom` | on any failure | `RestoreDrillFailed` — a failure more recent than the last success |

`RestoreStale` is what catches a timer that stopped running: it writes nothing, and `absent()`
turns that silence into an alert. A clean run removes `restore-failure.prom`, so a recovered
drill stops `RestoreDrillFailed` on the next evaluation.

Run it by hand:

```bash
cd /opt/letmegetin
set -a; . /etc/letmegetin/infisical.env; set +a
RESTORE_DRILL_ENV_FILE=/opt/letmegetin-env/development.env STACK=lmgi-dev \
  ./scripts/with-secrets.sh ./scripts/restore-drill.sh
```

**Prove each failure path.** `RESTORE_DRILL_FAULT` injects one fault at the stage it is meant
to exercise, so the drill still runs its real pipeline and fails on a real fault:

| Value | Injected | Surfaces as |
|---|---|---|
| `checksum` | the downloaded `.sha256` is corrupted | `sha256sum -c` fails before anything is restored |
| `truncate` | 4 KiB cut off the dump after extraction | `pg_restore` fails on a truncated archive |
| `revision` | `alembic_version` rewritten in the scratch DB | the revision assertion fails |

Each exits non-zero, writes `restore-failure.prom` and leaves `restore.prom` untouched — check
both markers after the run, then run it once without the variable to clear the failure.

## TLS

- Caddy obtains and renews certificates automatically. Check `docker compose logs caddy` for ACME
  errors.
- Do not expose the API or web ports; only Caddy publishes 80/443.
- HSTS is set by Caddy; keep the domains HTTPS-only.

## Monitoring and errors

- Prometheus and Alertmanager run as their own Compose project, `lmgi-monitoring`, brought up by the
  config repo's deploy — they are not services of `docker-compose.prod.yml` and have no profile.
- Prometheus scrapes `lmgi-prod-api:8000/metrics` over the shared `lmgi-edge` network. The public
  `/metrics` path stays a 404.
- Alerts: API down, 5xx rate, 429 rate, Redis down → Alertmanager → Discord, the channel the rest of
  the stack reports to. The webhook comes from Infisical (`ALERT_WEBHOOK`); the config repo renders
  it to a 0600 file and fails the deploy when it is missing.
- Sentry captures API and web exceptions (no request bodies, no PII; emails redacted). Without a
  DSN it is disabled; the API logs a production warning when `LETMEGETIN_SENTRY_DSN` is missing.
- Useful signals: `letmegetin_http_requests_total`, `letmegetin_rate_limited_total`,
  `letmegetin_redis_up`, `/health`, Caddy logs.

### Prove an alert end to end

`ApiDown` fires on `up{job="letmegetin-api"} == 0` after `for: 2m`, and Alertmanager waits
`group_wait: 30s`, so the Discord message lands about three minutes after the API stops. Do it at a
low-traffic moment, restart the API as soon as the alert is observed, and budget four minutes:

```bash
# on the host, as root; the runner is the only way to reach this Compose project
/usr/local/bin/letmegetin-compose /opt/letmegetin-env/production.env lmgi-prod stop api
sleep 180
curl -fsS 'http://127.0.0.1:9093/api/v2/alerts?active=true'   # holds alertname="ApiDown"
/usr/local/bin/letmegetin-compose /opt/letmegetin-env/production.env lmgi-prod start api
```

The receiver's own record is the message in the Discord channel the webhook points at: a webhook
cannot read the channel back, so confirm it there rather than in Alertmanager's UI. From the host,
`curl -fsS http://127.0.0.1:9093/metrics | grep 'notifications_total{integration="discord"}'` counts
the dispatches and `…_failed_total` must stay `0`. `Notify success` is logged at debug level only, so
an INFO-level log says nothing either way.

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
