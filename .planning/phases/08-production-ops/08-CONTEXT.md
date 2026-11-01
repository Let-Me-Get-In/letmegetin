# Phase 8: Production Deployment & Operations — Context

**Gathered:** 2026-10-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Take the Phase 7 compose stack to a production-grade, host-agnostic deployment:

- TLS termination and production secrets.
- Postgres/Redis backups with a tested restore.
- Metrics, monitoring and alerting.
- Retention jobs for idempotency and session data.
- A runbook for deploy, rollback, restore and incidents.

Out of scope: cloud-specific IaC (Terraform), multi-region/HA, WAF, a paid observability vendor.
</domain>

<decisions>
## Decisions

- **Host-agnostic**: any Linux VPS with Docker and two DNS names (`app.` and `api.`). **Caddy**
  terminates TLS (automatic certificates), reverse-proxies the web and API, and applies security
  headers. Only 80/443 are published; API and web stay on the internal network.
- **Secrets** live in `deploy/.env.prod` (git-ignored): Postgres password, **Redis password**,
  `LETMEGETIN_JWT_SECRET`, SMTP. Compose reads them; no secret in a committed file.
- **Backups**: `pg_dump` custom format + Redis RDB snapshot, timestamped, 7 daily local retention
  and an **offsite Cloudflare R2 upload** (Wrangler, API token, checksum). A restore
  script restores into a **scratch database** first; the runbook includes the restore test, not only
  the backup command.
- **Metrics**: `prometheus-client` on the API at `/metrics` (internal network only, not routed by
  Caddy): request count/status, latency histogram, 429 count, Redis-up gauge. Prometheus scrapes
  it; alert rules cover API down, 429 spikes, Redis down, 5xx rate. Alertmanager receives the
  alerts via a configurable webhook.
- **Error tracking: Sentry, DSN-gated**. Backend `sentry-sdk[fastapi]` and web `@sentry/nextjs`,
  EU region, `send_default_pii=False`, request bodies/headers scrubbed, release = git SHA,
  sample 10 %. Without a DSN, Sentry is a no-op. It complements Prometheus: metrics tell us *that*
  something is wrong, Sentry tells us *where*.
- **PostHog is deferred**. Product analytics needs a consent/CMP, a privacy review (session replay
  of accessibility contributions is sensitive) and an accessibility review of the injected
  script. It is not an operations need; revisit after V1.1 in a dedicated ticket.
- **Retention** is an operator CLI command (`letmegetin-admin retention`) scheduled by systemd
  timers: idempotency keys older than 24h, expired/revoked refresh tokens older than 30 days.
  Contributions and reviews are audit data and are never purged.
- **Runbook** is checked in (`docs/runbook.md`): deploy, rollback, restore, TLS renewal, incident,
  retention.
</decisions>

<canonical_refs>
- `.planning/REQUIREMENTS.md` — OPS-04, OPS-05, OPS-06.
- `.planning/ROADMAP.md` — Phase 8 success criteria.
- `docker-compose.prod.yml` — the Phase 7 stack (PostGIS + Redis + API + web).
- `docs/deploy.md` — current deployment notes.
- `src/letmegetin/main.py` — app factory, `/health`, `/metrics` to add.
</canonical_refs>

<code_context>
- The prod compose publishes API :8000 and web :3000 directly; Phase 8 removes those host ports.
- Redis has no password today; the production URL must support one.
- The API has `/health` but no metrics endpoint.
- `letmegetin-admin` is the write/ops CLI; retention fits there.
- Backups have no scripts yet.
</code_context>

<deferred>
- Terraform/Ansible, multi-region, HA Postgres, managed Redis, WAF, paging integrations.
- **PostHog / product analytics**: consent, privacy and accessibility review first; later ticket.
</deferred>

---
*Phase: 08-production-ops*
