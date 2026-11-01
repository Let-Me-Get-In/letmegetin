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

# Keep the most recent N archives.
ls -1t "$DEST"/*.tar.gz | tail -n +$((KEEP_DAILY + 1)) | xargs -r rm -f
