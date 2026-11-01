#!/usr/bin/env bash
# Restore a backup into a scratch database, verify counts, optionally promote.
# Usage: restore.sh <backup.tar.gz> [--promote]
set -euo pipefail

ARCHIVE=${1:?usage: restore.sh <backup.tar.gz> [--promote]}
PROMOTE=${2:-}
STACK=${STACK:-letmegetin-prod}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

compose() { docker compose -p "$STACK" -f "$COMPOSE_FILE" "$@"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
tar -xzf "$ARCHIVE" -C "$TMP"
DIR=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)
test -n "$DIR" || { echo "no backup directory in $ARCHIVE" >&2; exit 1; }

compose exec -T db dropdb -U letmegetin --if-exists letmegetin_restore
compose exec -T db createdb -U letmegetin letmegetin_restore
compose exec -T db pg_restore -U letmegetin -d letmegetin_restore \
  --clean --if-exists --no-owner < "$DIR/db.dump"

echo "restored into letmegetin_restore:"
for table in place categories review users; do
  count=$(compose exec -T db psql -U letmegetin -d letmegetin_restore -tAc "select count(*) from $table")
  echo "  $table=$count"
done

if [ "$PROMOTE" = "--promote" ]; then
  echo "promoting the scratch database (destructive)..."
  compose stop api
  compose exec -T db psql -U letmegetin -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'letmegetin' AND pid <> pg_backend_pid()" >/dev/null
  compose exec -T db dropdb -U letmegetin --if-exists letmegetin
  compose exec -T db createdb -U letmegetin -T letmegetin_restore letmegetin
  compose start api
  echo "promoted; verify /health before reopening traffic."
else
  echo "scratch database kept as letmegetin_restore; rerun with --promote to swap it in."
fi
