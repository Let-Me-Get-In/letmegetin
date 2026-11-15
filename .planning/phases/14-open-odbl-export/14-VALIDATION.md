---
phase: "14"
slug: "open-odbl-export"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-15"
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|---------|
| **Framework** | pytest 9.1.1 (+ pytest-asyncio, httpx/TestClient) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, markers `unit`/`integration`/`functional`) |
| **Quick run command** | `uv run pytest -m "unit or integration" -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~135 s (486 tests, functional suite against PostGIS) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -m "unit or integration" -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 135 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | EXP-01 | T-14-01 | every place write journals in the same transaction | functional | `uv run pytest tests/functional/places/test_export_event.py -m functional -q` | ✅ | ✅ green |
| 14-01-02 | 01 | 1 | EXP-01 | T-14-01, T-14-17 | rejected and no-op writes append nothing; `safe_seq` excludes in-flight transactions | unit + functional | `uv run pytest tests/unit/infrastructure/persistence/test_export_event_chokepoints.py tests/functional/places/test_export_event.py -q` | ✅ | ✅ green |
| 14-01-03 | 01 | 1 | EXP-01 | T-14-02 | operator history reads the journal only | unit | `uv run pytest tests/unit/application/places/test_history.py -q` | ✅ | ✅ green |
| 14-02-01 | 02 | 2 | EXP-01, EXP-02 | T-14-04, T-14-12 | answer licence filter is fail-closed (SQL); CSV guard is per column | unit + functional | `uv run pytest tests/unit/application/places/test_export.py tests/functional/places/test_export.py -q` | ✅ | ✅ green |
| 14-02-02 | 02 | 2 | EXP-01, EXP-02 | T-14-16, T-14-17 | snapshot/delta/catch-up on the MVCC boundary; retention prunes only the past | functional | `uv run pytest tests/functional/places/test_export.py -m functional -q` | ✅ | ✅ green |
| 14-02-03 | 02 | 2 | EXP-01 | T-14-16 | CLI writes the seven-file ZIP, the delta and the catch-up | functional | `uv run pytest tests/functional/places/test_export.py -m functional -q` | ✅ | ✅ green |
| 14-03-01 | 03 | 3 | EXP-01 | T-14-07 | `{name}` never escapes the export directory | functional | `uv run pytest tests/functional/api/test_export.py -m functional -q` | ✅ | ✅ green |
| 14-03-02 | 03 | 3 | EXP-01 | T-14-08 | the volume is read-only in the api service | none — see Manual-Only | — | ⚠️ no test | ⚠️ manual |
| 14-04-01 | 04 | 4 | EXP-02 | T-14-10 | the partner doc reads the shared attribution constants | integration | `uv run pytest tests/integration/api/test_openapi.py -m integration -q` | ✅ | ✅ green |
| 14-05-01 | 05 | 4 | EXP-01 | T-14-14 | the wrapper accepts only `snapshot\|delta` and builds a fixed argv | unit | `uv run pytest tests/unit/scripts/test_export_odbl_wrapper.py -q` | ✅ | ✅ green |
| 14-05-02 | 05 | 4 | EXP-01 | T-14-13 | Actions carries no DB/API secret | none — see Manual-Only | — | ⚠️ no test | ⚠️ manual |
| 14-05-03 | 05 | 4 | EXP-01, EXP-02 | T-14-10 | the ops runbook matches the shipped units and the writable mount | none — see Manual-Only | — | ⚠️ no test | ⚠️ manual |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⚠️ manual (no automated check — listed under Manual-Only)*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements: the phase added no framework, no dependency, and its tests slot into the existing `tests/unit`, `tests/integration` and `tests/functional` layers with the shared PostGIS fixtures.

---

## Manual-Only Verifications

| Behavior | Requirement | Why manual | Test Instructions |
|----------|-------------|------------|-------------------|
| systemd units load and fire on Linux | EXP-01 | no systemd on macOS, where the phase was built | `systemd-analyze verify deploy/systemd/letmegetin-export-odbl-*.{service,timer}`, then `systemctl enable --now` and `systemctl list-timers` (expect Mon 04:00 / daily 03:15) |
| `workflow_dispatch` reaches the real host | EXP-01 | the host does not exist yet; the three `DEPLOY_*` secrets and the fingerprint variable are placeholders | set the secrets, allowlist the runner IP, dispatch `snapshot` then `delta` (LET-125) |
| Legal review of the three `attribution_text` sentences | EXP-02 | legal judgement, not testable | compare `data/referential/licences.csv` against each licence's required wording (LET-126) |
| Partner contract wording | EXP-02 | prose review | read `## ODbL export` in `docs/public-api.md` (LET-126) |
| `export_data` is mounted read-only in the api service | EXP-01 | no test parses `docker-compose.prod.yml`; the assertion was run by hand | `docker compose -f docker-compose.prod.yml config` → `read_only: true`, `LETMEGETIN_EXPORT_DIR: /data/export` |
| The workflow file carries no DB/API secret | EXP-01 | no test parses the YAML; checked by hand | `grep -n "secrets\." .github/workflows/export-odbl.yml` → only `DEPLOY_*` |
| The runbook matches the shipped units and the writable mount | EXP-01, EXP-02 | the doc assertion in the plan was never turned into a test | compare `## ODbL export` in `docs/deploy.md` with `deploy/systemd/*` and `scripts/export-odbl.sh` (LET-125) |

---

## Validation Audit Trail

| Audit Date | Gaps Found | Resolved | Escalated | Run By |
|------------|------------|----------|-----------|--------|
| 2026-11-15 | 0 | 0 | 0 | orchestrator (State B reconstruction) |

---

## Sign-Off

- [x] Every requirement (EXP-01, EXP-02) maps to at least one automated command
- [x] Every automated command was green on `cf35330`
- [x] Manual-only items are named, owned and not requirement-blocking
- [x] `nyquist_compliant: true`
