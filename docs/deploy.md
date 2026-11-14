# Deployment

The production stack is **Caddy + web + API + PostGIS + Redis**. Only Caddy publishes ports
(80/443); the API and web listen on the internal network. Metrics are internal only.

Secrets come from **Infisical**; the repository never holds a production `.env`.

The project is pinned: **`39c0bbf4-d1c8-476e-ae35-8d82c998d704`**, environment `prod`,
path `/`, EU Cloud (`https://eu.infisical.com`). `scripts/with-secrets.sh` refuses
any other project id, so a stray bootstrap file cannot read the wrong secrets.

## Secrets — Infisical

1. Install the [Infisical CLI](https://infisical.com/docs/cli/overview) on the host.
2. Create a **machine identity** (Universal Auth), add it to the project with read access, and
   create a client secret.
3. Create the bootstrap file (only the identity lives there):

   ```bash
   sudo install -d -m 700 /etc/letmegetin
   sudo cp deploy/infisical.env.example /etc/letmegetin/infisical.env
   sudo chmod 600 /etc/letmegetin/infisical.env
   # fill INFISICAL_PROJECT_ID, INFISICAL_DOMAIN (EU/self-hosted), CLIENT_ID, CLIENT_SECRET
   ```

4. Put the application secrets in the project's **prod** environment, path `/`:

   `ROOT_DOMAIN`, `APP_DOMAIN`, `API_DOMAIN`, `ACME_EMAIL`,
   `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `LETMEGETIN_JWT_SECRET`,
   `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `R2_BUCKET`, `R2_PREFIX`,
   `R2_JURISDICTION` (optional), `LETMEGETIN_SMTP_*`, `LETMEGETIN_SENTRY_DSN`,
   `NEXT_PUBLIC_SENTRY_DSN`, `ALERT_WEBHOOK`, `API_KEY` (leave empty for the web), `GIT_SHA`.

5. Every production command goes through the wrapper:

   ```bash
   ./scripts/with-secrets.sh <command>
   ```

   It logs in with the machine identity (or uses `INFISICAL_TOKEN`) and runs
   `infisical run --projectId … --env prod --path / -- <command>`.

`deploy/.env.prod.example` is kept only as a **fallback/reference** if Infisical is unavailable;
it is not the production path.

## First deploy

```bash
export INFISICAL_DOMAIN=https://eu.infisical.com   # EU Cloud; omit for US Cloud

./scripts/with-secrets.sh docker compose -p letmegetin-prod \
  -f docker-compose.prod.yml up -d --build

./scripts/with-secrets.sh docker compose -p letmegetin-prod \
  -f docker-compose.prod.yml exec api python -m letmegetin.seed
```

- Landing: `https://$ROOT_DOMAIN` (public marketing page)
- Web: `https://$APP_DOMAIN`
- API: `https://$API_DOMAIN` (`/health`, `/docs`, `/openapi.json`)
- `/metrics` is **not** routed publicly; Prometheus scrapes `lmgi-prod-api:8000` internally.
- Migrations run on API start (entrypoint).
- The compose project is `letmegetin-prod`; it never shares volumes with the dev PostGIS.

## The shared TLS edge

Only one container can publish 80/443, so the edge is its own compose project
(`lmgi-edge`, `deploy/vps/docker-compose.edge.yml`) and every stack joins the
`lmgi-edge` network. Its `Caddyfile` serves one block per hostname: the apex pair
(`ROOT_DOMAIN` / `www.ROOT_DOMAIN`) serves the public landing, the `APP_DOMAIN` /
`API_DOMAIN` pair reaches `lmgi-prod-api` / `lmgi-prod-web`, and the `dev.` pair
reaches `lmgi-dev-*`.

The network must exist first, or a stack whose `networks.edge` is `external`
refuses to start:

```bash
docker network create lmgi-edge
docker compose -p lmgi-edge -f deploy/vps/docker-compose.edge.yml up -d
```

Each stack then runs from `docker-compose.prod.yml` with `EDGE_API_ALIAS` /
`EDGE_WEB_ALIAS` set (the config repo renders them from the values file's
`project`). The aliases are qualified on purpose: Compose publishes the bare
service name `api` on every network a service joins, so two stacks would both
answer to it and a hostname could reach the wrong environment.

The local TLS smoke test is gone with the extraction — a throwaway stack now
needs the edge project too, and the config repo's `deploy` playbook is the
supported path.

## Monitoring

Prometheus and Alertmanager are their own Compose project, `lmgi-monitoring`, deployed by the config
repo — this repository only carries their configuration (`deploy/prometheus/`,
`deploy/alertmanager/`), which the config repo mounts from the shipped checkout. Nothing here starts
them, and there is no `observability` profile to enable.

Prometheus scrapes `lmgi-prod-api:8000/metrics` over the shared `lmgi-edge` network; alerts cover
API down, 5xx rate, 429 rate and Redis down, and Alertmanager posts them to Discord through the
webhook the config repo renders from `ALERT_WEBHOOK`.

## Required secret names (Infisical, env `prod`)

| Variable | Purpose |
|---|---|
| `ROOT_DOMAIN`, `APP_DOMAIN`, `API_DOMAIN`, `ACME_EMAIL` | Caddy TLS |
| `POSTGRES_PASSWORD`, `REDIS_PASSWORD` | internal services |
| `LETMEGETIN_JWT_SECRET` | **required**, long random string |
| `LETMEGETIN_ENVIRONMENT` | `production` |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `R2_BUCKET`, `R2_PREFIX` | offsite R2 backups |
| `LETMEGETIN_SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN` | optional error tracking |
| `LETMEGETIN_SMTP_*` | verification emails (otherwise logged) |
| `ALERT_WEBHOOK` | Discord webhook — rendered to a 0600 file at deploy time, never a Compose variable |
| `API_KEY` | leave empty for the public web; partner keys are server-side |

## ODbL export

The partner export is generated on the host and served by the API from one named volume,
`export_data`:

- The operator CLI writes `latest.json` and the snapshot/delta ZIPs into the volume. The API
  mounts it **read-only** at `LETMEGETIN_EXPORT_DIR` (`/data/export`) and serves
  `/api/v1/export/latest.json` and `/api/v1/export/<name>.zip` under the anonymous rate limit. It
  never writes the directory and never generates an archive.
- One-off generation needs the same volume read-**write**. Compose appends `-v` mounts to the
  service's own list instead of replacing it, so `run -v …:/data/export:rw` is still refused as
  read-only; `scripts/export-odbl.sh` mounts the volume at a second, writable target and points
  `--out` at it:

  ```bash
  # what the wrapper runs, once per generation
  docker compose -p letmegetin-prod -f docker-compose.prod.yml \
    run --rm -T -v export_data:/data/export-rw api \
    letmegetin-admin export odbl --out /data/export-rw [--delta]
  ```

- Nothing in the volume is secret. `latest.json.lock` and the transient `.<name>.zip.tmp` files
  sit there too; the API never serves or indexes them.

### Generation — wrapper and timers

`scripts/export-odbl.sh {snapshot|delta}` is the generation entry point. It bakes in no secret and
is always run under `scripts/with-secrets.sh`:

```bash
./scripts/with-secrets.sh ./scripts/export-odbl.sh snapshot   # weekly
./scripts/with-secrets.sh ./scripts/export-odbl.sh delta      # daily
```

`delta` passes `--delta`: the export command reads the watermark from `latest.json` under its own
`flock` and advances it only after the delta ZIP is written and fsynced, so a failed run re-emits
the same window and a delta is never cumulative. `--since <snapshot_seq>` remains the cumulative
catch-up for a partner who lost a delta, and is refused below `retention_floor_seq`.

Two timers, each with its own service, because the mode is the `ExecStart` argument
(`deploy/systemd/`):

| Timer | Schedule | Service `ExecStart` |
|---|---|---|
| `letmegetin-export-odbl-snapshot.timer` | `OnCalendar=Mon *-*-* 04:00:00` | `ExecStart=/opt/letmegetin/scripts/with-secrets.sh /opt/letmegetin/scripts/export-odbl.sh snapshot` |
| `letmegetin-export-odbl-delta.timer` | `OnCalendar=*-*-* 03:15:00` | `ExecStart=/opt/letmegetin/scripts/with-secrets.sh /opt/letmegetin/scripts/export-odbl.sh delta` |

The services are `Type=oneshot` and the timers carry `Persistent=true`, so a host that was down at
the scheduled time runs the unit on the next boot. Enable them once:

```bash
systemctl enable --now letmegetin-export-odbl-snapshot.timer letmegetin-export-odbl-delta.timer
```

### On demand — GitHub Actions

`.github/workflows/export-odbl.yml` is `workflow_dispatch` only, with a `delta`/`snapshot` choice:
it SSHes to the host and runs the same wrapper. No database credential and no API secret ever
enters Actions — only the SSH connection does; the database and API secrets are read on the host by
`with-secrets.sh`.

Prerequisites before the first run:

- `DEPLOY_HOST` (host name), `DEPLOY_USER` (SSH user) and `DEPLOY_SSH_KEY` (private host key) as
  **Actions secrets**;
- `DEPLOY_HOST_FINGERPRINT` (the host's SHA256 public-key fingerprint) as a repository
  **variable** — public data, not a secret. Set it: the action then refuses a host whose key does
  not match. Unset, the action does not verify the host key at all;
- the host firewall allowlists the Actions runner IP for the run and closes it after
  ([rules/deploy.md](rules/deploy.md) — "SSH closed by default", no standing `0.0.0.0/0` rule,
  host keys verified).

### Retention and the import

- **Retention is automatic; there is no separate export job.** After each snapshot the export
  command prunes `export_event` to the **previous** snapshot boundary — never the current one, so a
  replay from either of the last two snapshots stays possible — and deletes the delta ZIPs the new
  snapshot subsumes plus any orphan `delta-*.zip`, all inside the same `flock`. `letmegetin-retention`
  is a different job (refresh tokens, idempotency keys).
- **The AccesLibre import is untouched and stays atomic.** It commits the whole run in a single
  transaction, exactly as before: the MVCC boundary removed the per-transaction event cap, so there
  is no chunking and no resumability contract to honour.

## Operations

- After a deploy that changes the referential seed, fill the handicap families and
  check them: `./scripts/with-secrets.sh docker compose -p letmegetin-prod -f
  docker-compose.prod.yml exec api letmegetin-admin families sync`, then
  `… families audit` — it exits `1` while any criterion or filter has no family.
- First Acceslibre load on a host: download the *établissements* CSV from
  data.gouv.fr (Etalab 2.0), `… exec api letmegetin-admin import acceslibre --file
  /tmp/acceslibre.csv --dry-run`, complete `data/referential/acceslibre_categories.csv`
  until `unresolved=0`, import for real, then `… import report` (exit `0`).
- Backups/restore: `./scripts/with-secrets.sh ./scripts/backup.sh` (R2 via signed S3 `curl`),
  `./scripts/with-secrets.sh ./scripts/restore.sh <archive>`.
- Retention: `./scripts/with-secrets.sh docker compose … exec api letmegetin-admin retention`.
- Systemd timers read `/etc/letmegetin/infisical.env`; see `deploy/systemd/`.
- Runbook: [runbook.md](runbook.md).
- Changing a secret in Infisical requires **restarting the affected containers**; `infisical run`
  injects at process start.
