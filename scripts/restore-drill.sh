#!/usr/bin/env bash
# Offsite restore drill: download the newest archive from the backup bucket, verify it,
# restore it into the development stack's scratch database, assert the restored content
# against the deployed schema, then record the outcome as a marker file that Prometheus
# reads through node_exporter's textfile collector.
#
# Production is never named here. The drill restores into `letmegetin_restore` in the
# development stack only, and has no promote path -- restoring a production copy into
# production stays a human decision (`scripts/restore.sh`).
#
# Environment:
#   RESTORE_DRILL_ENV_FILE  values file of the target environment (required); sourced
#                           after Infisical injected the project, so it wins a collision
#   STACK                   compose project to restore into (default lmgi-dev)
#   COMPOSE_FILE            compose file (default docker-compose.prod.yml)
#   POSTGRES_DB             reference database the restored copy is asserted against
#   NODE_TEXTFILE_DIR       where the success and failure markers are written
#   R2_* / cf_backup_*      bucket and credentials, same fallback chain as backup.sh
#   RESTORE_DRILL_FAULT     inject one fault, to prove a failure path on a real run:
#                             checksum  corrupt the downloaded .sha256
#                             truncate  cut 4 KiB off the dump before pg_restore
#                             revision  rewrite alembic_version in the scratch database
set -euo pipefail

STACK=${STACK:-lmgi-dev}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
RESTORE_DRILL_FAULT=${RESTORE_DRILL_FAULT:-}

compose() { docker compose -p "$STACK" -f "$COMPOSE_FILE" "$@"; }

: "${RESTORE_DRILL_ENV_FILE:?restore-drill needs RESTORE_DRILL_ENV_FILE}"

# The values file is sourced here, inside the `with-secrets.sh` child, after Infisical
# injected the whole project: that ordering is what makes POSTGRES_DB, the edge aliases
# and the textfile directory win a name collision with a secret.
set -a
# shellcheck disable=SC1090
. "$RESTORE_DRILL_ENV_FILE"
set +a

: "${POSTGRES_DB:?POSTGRES_DB is required (it is the reference the restore is asserted against)}"

WORK=""

# Writes one textfile marker atomically, so the collector never reads a partial file.
# Best-effort on purpose: a missing directory or a failed write warns and lets the
# drill finish. A marker that is never written is itself an alert condition, so the
# failure to write one is not worth turning a clean restore into a failed run.
write_marker() {
  if [ -z "${NODE_TEXTFILE_DIR:-}" ] || [ ! -d "$NODE_TEXTFILE_DIR" ]; then
    echo "WARNING: NODE_TEXTFILE_DIR unset or missing; $1 not written" >&2
    return 0
  fi
  tmp="$NODE_TEXTFILE_DIR/$1.$$"
  if { printf '%s %s\n' "$2" "$(date +%s)" > "$tmp" 2>/dev/null \
      && mv -f "$tmp" "$NODE_TEXTFILE_DIR/$1" 2>/dev/null \
      && [ -s "$NODE_TEXTFILE_DIR/$1" ]; }; then
    return 0
  fi
  rm -f "$tmp"
  echo "WARNING: $1 not written to $NODE_TEXTFILE_DIR" >&2
  return 0
}

# The drill's one exit path. A non-zero status records the failure and names the kept
# scratch database -- the next person to look needs the evidence. The success marker is
# refreshed only after every assertion passed, so it is untouched here: "the last failure
# is more recent than the last success" stays evaluable. `exit "$rc"` last, so no command
# in this trap can mask the real result.
cleanup() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    write_marker restore-failure.prom letmegetin_restore_last_failure_timestamp_seconds
    echo "drill failed (rc=$rc): scratch database kept as letmegetin_restore" >&2
  fi
  if [ -n "$WORK" ]; then rm -rf "$WORK"; fi
  exit "$rc"
}
trap cleanup EXIT

R2_ACCESS_KEY_ID=${R2_ACCESS_KEY_ID:-${cf_backup_access_key_id:-}}
R2_SECRET_ACCESS_KEY=${R2_SECRET_ACCESS_KEY:-${cf_backup_secret_access_key:-}}
R2_ACCOUNT_ID=${R2_ACCOUNT_ID:-${cf_account_id:-}}
R2_BUCKET=${R2_BUCKET:-${cf_backup_bucket:-}}
R2_PREFIX=${R2_PREFIX:-letmegetin}
R2_JURISDICTION=${R2_JURISDICTION:-}
R2_ENDPOINT=${R2_ENDPOINT:-}

if [ -z "$R2_ENDPOINT" ] && [ -n "$R2_ACCOUNT_ID" ]; then
  R2_ENDPOINT="https://$R2_ACCOUNT_ID${R2_JURISDICTION:+.$R2_JURISDICTION}.r2.cloudflarestorage.com"
fi

: "${R2_BUCKET:?cf_backup_bucket / R2_BUCKET is required}"
: "${R2_ACCESS_KEY_ID:?cf_backup_access_key_id / R2_ACCESS_KEY_ID is required}"
: "${R2_SECRET_ACCESS_KEY:?cf_backup_secret_access_key / R2_SECRET_ACCESS_KEY is required}"
: "${R2_ENDPOINT:?cf_account_id or R2_ENDPOINT is required}"

WORK=$(mktemp -d)
DL="$WORK/download"
EX="$WORK/extract"
mkdir -p "$DL" "$EX"

s3() {
  curl -fsS --aws-sigv4 "aws:amz:auto:s3" \
    --user "$R2_ACCESS_KEY_ID:$R2_SECRET_ACCESS_KEY" "$@"
}

# 1. The bucket listing, signed against the endpoint computed above (the jurisdiction
#    suffix lives in it, so the host is never hard-coded). The timestamp names sort
#    newest-last, so the lexicographically largest request is the newest archive.
s3 "$R2_ENDPOINT/$R2_BUCKET?list-type=2&prefix=$R2_PREFIX/" > "$WORK/index.xml"
KEY=$(grep -o '<Key>[^<]*\.tar\.gz</Key>' "$WORK/index.xml" \
  | sed -e 's|<Key>||' -e 's|</Key>||' | sort | tail -1)
if [ -z "$KEY" ]; then
  echo "no archive under $R2_PREFIX/ in $R2_BUCKET" >&2
  exit 1
fi
NAME=$(basename "$KEY")
echo "drill: newest archive $KEY"

# 2. The archive and its checksum, into a fresh working copy. The local `backups/`
#    directory is never the source: the point is to prove the copy that left the
#    machine comes back.
s3 "$R2_ENDPOINT/$R2_BUCKET/$KEY" -o "$DL/$NAME"
s3 "$R2_ENDPOINT/$R2_BUCKET/$KEY.sha256" -o "$DL/$NAME.sha256"

if [ "$RESTORE_DRILL_FAULT" = checksum ]; then
  echo "fault=checksum: sha256 mismatch" >&2
  printf '%064d  %s\n' 0 "$NAME" > "$DL/$NAME.sha256"
fi

# 3. Verify the downloaded bytes before anything is replayed into Postgres.
(cd "$DL" && sha256sum -c "$NAME.sha256")

# 4. Unpack; the archive holds exactly one directory, like the local backup it came from.
tar -xzf "$DL/$NAME" -C "$EX"
DIR=$(find "$EX" -mindepth 1 -maxdepth 1 -type d | head -1)
if [ -z "$DIR" ]; then
  echo "no backup directory in $NAME" >&2
  exit 1
fi

if [ "$RESTORE_DRILL_FAULT" = truncate ]; then
  echo "fault=truncate: archive truncated" >&2
  truncate -s -4096 "$DIR/db.dump"
fi

# 5. Restore into the scratch database of the development stack.
compose exec -T db dropdb -U letmegetin --if-exists "letmegetin_restore"
compose exec -T db createdb -U letmegetin "letmegetin_restore"
compose exec -T db pg_restore -U letmegetin -d "letmegetin_restore" \
  --clean --if-exists --no-owner < "$DIR/db.dump"

if [ "$RESTORE_DRILL_FAULT" = revision ]; then
  echo "fault=revision: alembic revision mismatch" >&2
  compose exec -T db psql -U letmegetin -d "letmegetin_restore" -c \
    "UPDATE alembic_version SET version_num = '0000'" >/dev/null
fi

# 6. Assert the restored copy against the deployed reference, so a migration that adds a
#    table or a revision does not need this script edited. The reference is the
#    development database: dev and prod are deployed from the same checkout, so a
#    migration that reached one but not the other reds the drill until they match --
#    which is the honest signal that the backup no longer matches the deployed tree.
psql_ref() { compose exec -T db psql -U letmegetin -d "$POSTGRES_DB" -tAc "$1" | tr -d '[:space:]'; }
psql_scratch() { compose exec -T db psql -U letmegetin -d "letmegetin_restore" -tAc "$1" | tr -d '[:space:]'; }
TABLES="select count(*) from information_schema.tables where table_schema='public' and table_type='BASE TABLE'"

ref_tables=$(psql_ref "$TABLES")
ref_revision=$(psql_ref "select version_num from alembic_version")
tables=$(psql_scratch "$TABLES")
revision=$(psql_scratch "select version_num from alembic_version")

echo "restored: tables=$tables revision=$revision"
echo "deployed: tables=$ref_tables revision=$ref_revision ($POSTGRES_DB)"

if [ "$tables" != "$ref_tables" ]; then
  echo "FAIL: the restored copy has $tables public tables, $POSTGRES_DB has $ref_tables" >&2
  exit 1
fi
if [ "$revision" != "$ref_revision" ]; then
  echo "FAIL: the restored copy is at revision '$revision', $POSTGRES_DB is at '$ref_revision'" >&2
  exit 1
fi

for table in place categories place_accessibility; do
  count=$(psql_scratch "select count(*) from $table")
  echo "  $table=$count"
  if [ "${count:-0}" -le 0 ] 2>/dev/null; then
    echo "FAIL: $table is empty in the restored copy" >&2
    exit 1
  fi
done

# 7. Clean run: the scratch database has served its purpose.
compose exec -T db dropdb -U letmegetin --if-exists "letmegetin_restore"

# 8. The success marker, and the failure marker cleared -- a fresh success must leave
#    RestoreDrillFailed with nothing to fire on.
write_marker restore.prom letmegetin_restore_last_success_timestamp_seconds
if [ -n "${NODE_TEXTFILE_DIR:-}" ] && [ -d "$NODE_TEXTFILE_DIR" ]; then
  rm -f "$NODE_TEXTFILE_DIR/restore-failure.prom"
fi
echo "restore drill: ok ($KEY)"
