#!/usr/bin/env bash
# Back up Postgres and Redis of the production stack.
# Environment: POSTGRES_PASSWORD, REDIS_PASSWORD (systemd EnvironmentFile or export).
set -euo pipefail

STACK=${STACK:-letmegetin-prod}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
DEST=${BACKUP_DIR:-./backups}
KEEP_DAILY=${KEEP_DAILY:-7}

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${REDIS_PASSWORD:?REDIS_PASSWORD is required}"

compose() { docker compose -p "$STACK" -f "$COMPOSE_FILE" "$@"; }

TS=$(date -u +%Y%m%dT%H%M%SZ)
WORK="$DEST/$TS"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

compose exec -T db pg_dump -U letmegetin -Fc letmegetin > "$WORK/db.dump"
compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning SAVE >/dev/null
compose cp redis:/data/dump.rdb "$WORK/redis.rdb"

tar -czf "$DEST/$TS.tar.gz" -C "$DEST" "$TS"
echo "backup: $DEST/$TS.tar.gz"

# Offsite copy to Cloudflare R2 over its S3 API, with curl's own SigV4 signer.
# Backups authenticate with a bucket-scoped R2 key pair, not an account-wide API
# token: an account token that can rewrite every bucket has no business sitting
# in a nightly cron. curl is the only dependency -- no AWS CLI, no Wrangler.
R2_ACCESS_KEY_ID=${R2_ACCESS_KEY_ID:-${cf_backup_access_key_id:-}}
R2_SECRET_ACCESS_KEY=${R2_SECRET_ACCESS_KEY:-${cf_backup_secret_access_key:-}}
R2_ACCOUNT_ID=${cf_account_id:-}
R2_BUCKET=${R2_BUCKET:-${cf_backup_bucket:-}}
R2_PREFIX=${R2_PREFIX:-letmegetin}
R2_JURISDICTION=${R2_JURISDICTION:-}
R2_ENDPOINT=${R2_ENDPOINT:-}

if [ -z "$R2_ENDPOINT" ] && [ -n "$R2_ACCOUNT_ID" ]; then
  R2_ENDPOINT="https://$R2_ACCOUNT_ID${R2_JURISDICTION:+.$R2_JURISDICTION}.r2.cloudflarestorage.com"
fi

if [ -n "$R2_BUCKET" ]; then
  : "${R2_ACCESS_KEY_ID:?cf_backup_access_key_id is required for R2_BUCKET}"
  : "${R2_SECRET_ACCESS_KEY:?cf_backup_secret_access_key is required for R2_BUCKET}"
  : "${R2_ENDPOINT:?cf_account_id (or R2_ENDPOINT) is required for R2_BUCKET}"
  KEY="$R2_PREFIX/$(basename "$DEST/$TS.tar.gz")"

  # The checksum names the archive by basename, so `sha256sum -c` works on a
  # download without rewriting the path field first.
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$DEST" && sha256sum "$TS.tar.gz") > "$DEST/$TS.tar.gz.sha256"
  else
    (cd "$DEST" && shasum -a 256 "$TS.tar.gz") > "$DEST/$TS.tar.gz.sha256"
  fi

  put() {
    curl -fsS -X PUT \
      --aws-sigv4 "aws:amz:auto:s3" --user "$R2_ACCESS_KEY_ID:$R2_SECRET_ACCESS_KEY" \
      -H 'x-amz-content-sha256: UNSIGNED-PAYLOAD' -H "Content-Type: $3" \
      -T "$1" "$R2_ENDPOINT/$R2_BUCKET/$2" >/dev/null
  }
  put "$DEST/$TS.tar.gz" "$KEY" application/gzip
  put "$DEST/$TS.tar.gz.sha256" "$KEY.sha256" text/plain
  echo "offsite: r2://$R2_BUCKET/$KEY"

  # The backup-age marker Prometheus reads through node_exporter's textfile
  # collector. Only a successful offsite upload refreshes it: a local-only or
  # failed upload must let BackupStale fire.
  #
  # Best-effort: a failed write must not fail the backup after the offsite
  # upload. The temp file + rename is atomic, so the collector never reads a
  # partial file; `[ -s ]` asserts the rename left a non-empty file.
  if [ -n "${NODE_TEXTFILE_DIR:-}" ] && [ -d "$NODE_TEXTFILE_DIR" ]; then
    tmp="$NODE_TEXTFILE_DIR/backup.prom.$$"
    if printf 'lmgi_backup_last_success_timestamp_seconds %s\n' "$(date +%s)" > "$tmp" 2>/dev/null \
        && mv -f "$tmp" "$NODE_TEXTFILE_DIR/backup.prom" 2>/dev/null \
        && [ -s "$NODE_TEXTFILE_DIR/backup.prom" ]; then
      :
    else
      rm -f "$tmp"
      echo "WARNING: backup-age marker not written to $NODE_TEXTFILE_DIR (BackupStale will fire)" >&2
    fi
  else
    echo "WARNING: NODE_TEXTFILE_DIR unset or missing; backup-age signal not emitted" >&2
  fi
else
  echo "WARNING: no R2 bucket configured (cf_backup_bucket / R2_BUCKET); the backup is local only" >&2
fi

# Keep the most recent N local archives; remote retention is an object-store lifecycle rule.
ls -1t "$DEST"/*.tar.gz | tail -n +$((KEEP_DAILY + 1)) | xargs -r rm -f
