#!/usr/bin/env bash
# Run a command with Infisical secrets injected (machine identity or service token).
# Bootstrap file: /etc/letmegetin/infisical.env (mode 600), see deploy/infisical.env.example.
set -euo pipefail

# One project only (see AGENTS.md): a different id is a mistake, not a variant.
INFISICAL_PROJECT_ID=${INFISICAL_PROJECT_ID:-264a35e3-cdca-43b7-9bdd-ff437c5bf2e1}
if [ "$INFISICAL_PROJECT_ID" != "264a35e3-cdca-43b7-9bdd-ff437c5bf2e1" ]; then
  echo "with-secrets: refusing project '$INFISICAL_PROJECT_ID' (expected 264a35e3-cdca-43b7-9bdd-ff437c5bf2e1)" >&2
  echo "with-secrets: fix INFISICAL_PROJECT_ID in /etc/letmegetin/infisical.env" >&2
  exit 1
fi

: "${INFISICAL_ENVIRONMENT:=prod}"
: "${INFISICAL_PATH:=/}"

if [ -z "${INFISICAL_TOKEN:-}" ]; then
  : "${INFISICAL_CLIENT_ID:?INFISICAL_CLIENT_ID or INFISICAL_TOKEN is required}"
  : "${INFISICAL_CLIENT_SECRET:?INFISICAL_CLIENT_SECRET is required}"
  INFISICAL_TOKEN=$(infisical login \
    --method=universal-auth \
    --client-id "$INFISICAL_CLIENT_ID" \
    --client-secret "$INFISICAL_CLIENT_SECRET" \
    --silent --plain)
  export INFISICAL_TOKEN
fi

export INFISICAL_DISABLE_UPDATE_CHECK=true
exec infisical run \
  --projectId "$INFISICAL_PROJECT_ID" \
  --env "$INFISICAL_ENVIRONMENT" \
  --path "$INFISICAL_PATH" \
  -- "$@"
