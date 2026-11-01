---
status: complete
phase: 08-production-ops
source: 08-01-PLAN.md
started: 2026-11-01T19:30:00Z
updated: 2026-11-01T21:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. TLS edge
expected: Caddy terminates TLS for the web and API; `/docs` works; `/metrics` is not routed.
result: pass
source: runtime
evidence: "Local stack with Caddy internal TLS: app 200, api /health 200, /docs 200, /metrics 404 through Caddy."

### 2. Network isolation
expected: only Caddy publishes ports; API and web are internal.
result: pass
source: runtime
evidence: "compose exposes api:8000/web:3000 internally; only 80/443 are published. BFF /api/v1/categories works through the web host."

### 3. Backup
expected: a timestamped archive with the Postgres dump and Redis RDB is produced.
result: pass
source: runtime
evidence: "scripts/backup.sh produced /tmp/letmegetin-backups/<ts>.tar.gz with db.dump and redis.rdb."

### 4. Restore into scratch
expected: the archive restores into `letmegetin_restore`, counts match, and a deleted marker is recovered.
result: pass
source: runtime
evidence: "place=1 (marker), categories=158, review=0, users=0; the marker deleted before restore is back."

### 5. Metrics and alert rules
expected: `/metrics` exposes the request counter internally; Prometheus config/rules validate; Caddy config validates.
result: pass
source: automated
evidence: "internal /metrics contains letmegetin_http_requests_total; promtool check config + 4 rules pass; caddy validate passes (CI job)."

### 6. Sentry
expected: Sentry is a no-op without a DSN; the scrubber removes requests and redacts emails; the web builds with the SDK.
result: pass
source: automated
evidence: "2 unit tests; Next build with @sentry/nextjs succeeds without a DSN; request objects dropped, emails redacted."

### 7. Retention
expected: dry-run counts without deleting; the real run deletes only expired idempotency keys and refresh tokens.
result: pass
source: automated
evidence: "dry-run 1/1 leaving 2/2 rows; real run leaves 1/1; second dry-run 0/0. 2 unit + 2 integration tests."

### 8. Tests and CI
expected: backend and web suites pass; CI covers the new observability job.
result: pass
source: automated
evidence: "192 backend tests, 25 web tests; CI 10/10 (run 41346125526, including Observability config)."

### 9. Offsite backup
expected: the backup archive and its checksum are uploaded to an S3-compatible bucket.
result: pass
source: runtime
evidence: "S3-compatible mock: `letmegetin/<ts>.tar.gz` (31 KB) and `.sha256` uploaded via the AWS CLI container; bucket listing confirms both."

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

OPS-04's real host/DNS cutover remains an operator action; the artifacts are verified locally.
