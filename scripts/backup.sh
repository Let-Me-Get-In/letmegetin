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

# Offsite copy to Cloudflare R2 (or any S3-compatible store).
# R2_* names are the documented path; S3_*/AWS_* still work for other providers.
R2_ACCOUNT_ID=${R2_ACCOUNT_ID:-}
S3_BUCKET=${S3_BUCKET:-${R2_BUCKET:-}}
S3_PREFIX=${S3_PREFIX:-letmegetin}
S3_ENDPOINT_URL=${S3_ENDPOINT_URL:-${R2_ACCOUNT_ID:+https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com}}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-${R2_ACCESS_KEY_ID:-}}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-${R2_SECRET_ACCESS_KEY:-}}
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-auto}

if [ -n "$S3_BUCKET" ]; then
  : "${AWS_ACCESS_KEY_ID:?R2_ACCESS_KEY_ID (or AWS_ACCESS_KEY_ID) is required}"
  : "${AWS_SECRET_ACCESS_KEY:?R2_SECRET_ACCESS_KEY (or AWS_SECRET_ACCESS_KEY) is required}"
  KEY="${S3_PREFIX}/$(basename "$DEST/$TS.tar.gz")"

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$DEST/$TS.tar.gz" > "$DEST/$TS.tar.gz.sha256"
  else
    shasum -a 256 "$DEST/$TS.tar.gz" > "$DEST/$TS.tar.gz.sha256"
  fi

  ENDPOINT_ARGS=()
  if [ -n "${S3_ENDPOINT_URL:-}" ]; then
    ENDPOINT_ARGS=(--endpoint-url "$S3_ENDPOINT_URL")
  fi

  AWS_CLI="amazon/aws-cli:latest@sha256:d557b3524475d70dd3104cf44d96568ee3188897b73a6ece2b37aa50e1af362f"
  docker run --rm \
    -v "$DEST/$TS.tar.gz:/backup.tar.gz:ro" \
    -v "$DEST/$TS.tar.gz.sha256:/backup.tar.gz.sha256:ro" \
    -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
    -e AWS_DEFAULT_REGION="$AWS_DEFAULT_REGION" \
    "$AWS_CLI" ${ENDPOINT_ARGS[@]+"${ENDPOINT_ARGS[@]}"} \
    s3 cp /backup.tar.gz "s3://$S3_BUCKET/$KEY"
  docker run --rm \
    -v "$DEST/$TS.tar.gz.sha256:/backup.tar.gz.sha256:ro" \
    -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
    -e AWS_DEFAULT_REGION="$AWS_DEFAULT_REGION" \
    "$AWS_CLI" ${ENDPOINT_ARGS[@]+"${ENDPOINT_ARGS[@]}"} \
    s3 cp /backup.tar.gz.sha256 "s3://$S3_BUCKET/$KEY.sha256"
  echo "offsite: s3://$S3_BUCKET/$KEY"
else
  echo "WARNING: R2_BUCKET/S3_BUCKET is unset; the backup is local only" >&2
fi

# Keep the most recent N local archives; remote retention is an object-store lifecycle rule.
ls -1t "$DEST"/*.tar.gz | tail -n +$((KEEP_DAILY + 1)) | xargs -r rm -f
