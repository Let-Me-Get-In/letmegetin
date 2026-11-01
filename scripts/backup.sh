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

# Offsite copy to Cloudflare R2 through Wrangler (no AWS tooling).
R2_BUCKET=${R2_BUCKET:-}
R2_PREFIX=${R2_PREFIX:-letmegetin}
R2_JURISDICTION=${R2_JURISDICTION:-}

if [ -n "$R2_BUCKET" ]; then
  : "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN is required for R2_BUCKET}"
  : "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID is required for R2_BUCKET}"
  KEY="$R2_PREFIX/$(basename "$DEST/$TS.tar.gz")"

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$DEST/$TS.tar.gz" > "$DEST/$TS.tar.gz.sha256"
  else
    shasum -a 256 "$DEST/$TS.tar.gz" > "$DEST/$TS.tar.gz.sha256"
  fi

  JURISDICTION_ARGS=()
  if [ -n "$R2_JURISDICTION" ]; then
    JURISDICTION_ARGS=(--jurisdiction "$R2_JURISDICTION")
  fi

  NODE_IMAGE="node:22-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914"
  docker run --rm \
    -v "$DEST/$TS.tar.gz:/backup.tar.gz:ro" \
    -e CLOUDFLARE_API_TOKEN -e CLOUDFLARE_ACCOUNT_ID \
    "$NODE_IMAGE" npx --yes wrangler@4 r2 object put "$R2_BUCKET/$KEY" \
    --file=/backup.tar.gz --remote ${JURISDICTION_ARGS[@]+"${JURISDICTION_ARGS[@]}"}
  docker run --rm \
    -v "$DEST/$TS.tar.gz.sha256:/backup.tar.gz.sha256:ro" \
    -e CLOUDFLARE_API_TOKEN -e CLOUDFLARE_ACCOUNT_ID \
    "$NODE_IMAGE" npx --yes wrangler@4 r2 object put "$R2_BUCKET/$KEY.sha256" \
    --file=/backup.tar.gz.sha256 --remote ${JURISDICTION_ARGS[@]+"${JURISDICTION_ARGS[@]}"}
  echo "offsite: r2://$R2_BUCKET/$KEY"
else
  echo "WARNING: R2_BUCKET is unset; the backup is local only" >&2
fi

# Keep the most recent N local archives; remote retention is an object-store lifecycle rule.
ls -1t "$DEST"/*.tar.gz | tail -n +$((KEEP_DAILY + 1)) | xargs -r rm -f
