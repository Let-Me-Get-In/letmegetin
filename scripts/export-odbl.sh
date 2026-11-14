#!/usr/bin/env bash
# Generate the ODbL export on the host: a full snapshot or an MVCC-bounded delta.
#
# The api service mounts export_data at /data/export READ-ONLY. Compose appends
# `run -v` mounts to the service's list instead of replacing them, so overriding
# that target cannot relax it: the one-off container writes the same volume at a
# second, writable target and points --out at it.
#
#   ./scripts/with-secrets.sh ./scripts/export-odbl.sh {snapshot|delta}
set -euo pipefail

STACK=${STACK:-letmegetin-prod}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
OUT=${EXPORT_DIR_IN_CONTAINER:-/data/export-rw}

compose() { docker compose -p "$STACK" -f "$COMPOSE_FILE" "$@"; }

mode="${1:-snapshot}"

case "$mode" in
  snapshot)
    compose run --rm -T -v export_data:"$OUT" api \
      letmegetin-admin export odbl --out "$OUT"
    ;;
  delta)
    # The watermark lives in latest.json and is read and advanced by the export
    # command under its own flock; the wrapper never reads it.
    compose run --rm -T -v export_data:"$OUT" api \
      letmegetin-admin export odbl --out "$OUT" --delta
    ;;
  *)
    echo "usage: export-odbl.sh {snapshot|delta}" >&2
    exit 2
    ;;
esac
