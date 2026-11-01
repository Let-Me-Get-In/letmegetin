---
phase: 08-production-ops
verified: 2026-11-01T21:30:00Z
status: passed
score: 2/3 fully verified, OPS-04 partial (host cutover)
ticket: LET-23
branch: LET-23-production-ops-impl
plan: 08-01-PLAN.md
requirements:
  OPS-04: partial - TLS/Caddy/secrets/runbook shipped and verified locally; the real host/DNS cutover is an operator step
  OPS-05: satisfied - backup + scratch-DB restore, marker recovered
  OPS-06: satisfied - metrics, Prometheus alerts, Sentry, retention + timers
gates:
  ruff_check: pass
  ruff_format_check: pass
  mypy: pass
  bandit: pass
  pytest: pass (192 passed)
  web_lint: pass
  web_typecheck: pass
  web_tests: pass (25 Vitest tests)
  web_build: pass (Sentry SDK included, no DSN)
  promtool: pass (config + 4 rules)
  caddy_validate: pass
  compose_smoke: pass (Caddy TLS, health, docs, metrics blocked, BFF)
  backup_restore: pass (marker recovered)
  offsite_upload: pass (Wrangler command + checksum; live R2 not exercised)
  alembic_current: "0008 (head)"
  pr_checks: pass (10/10, run 41349628601)
gaps:
  - "OPS-04 host cutover: DNS, ACME certificates, production secrets and the first deploy on a real VPS remain."
warnings:
  - "Offsite upload uses Wrangler (no AWS); the command and flow are validated, but the R2 bucket/API token/lifecycle are operator settings and were not exercised against a live Cloudflare account."
  - "The Alertmanager webhook is a placeholder until a real chat/on-call endpoint is provided."
  - "Sentry is DSN-gated; until a DSN is set, errors are only visible in logs/metrics."
  - "Prometheus/Alertmanager/Caddy/Postgres/Redis images are pinned by digest; update them deliberately."
  - "The retention job only covers idempotency keys and refresh tokens; logs/backups have their own retention."
deferred:
  - item: "Terraform/Ansible, HA Postgres, managed Redis, WAF, paging"
    addressed_in: "Post-V1.1 / infrastructure work"
    evidence: "08-CONTEXT.md deferred list."
---

# Phase 8: Production Deployment & Operations Verification Report

**Phase goal (ROADMAP):** Run the stack on a real host with TLS, secrets, backups, monitoring and
retention.
**Ticket:** LET-23 · **Branch:** `LET-23-production-ops-impl` · **PR:** #16
**Verified:** 2026-11-01T21:30:00Z
**Method:** goal-backward against the code, the local compose stack with Caddy internal TLS, a
real backup/restore cycle, promtool/caddy validation and the test suites.

## Requirement evidence

| Requirement | Evidence |
|---|---|
| OPS-04 (partial) | Caddy terminates TLS (internal CA locally), API/web are not published, secrets come from `deploy/.env.prod`, Redis requires a password, `docs/runbook.md` covers deploy/rollback/restore. A real host + DNS + ACME + first deploy remain. |
| OPS-05 | `scripts/backup.sh` writes a Postgres custom dump + Redis RDB; `scripts/restore.sh` restores into `letmegetin_restore`, prints counts, and only promotes with `--promote`. Tested: marker recovered. |
| OPS-06 | `/metrics` internal, Prometheus scrapes it, 4 alert rules validated; Sentry captures errors with request removal/email redaction (DSN-gated); `letmegetin-admin retention` + daily timer. |

## Verified sequence

Caddy TLS → web 200 / api 200 → BFF categories → seed → marker → backup → delete marker →
restore scratch → marker recovered → promtool/caddy validate → retention dry-run/real.
