---
phase: 14-open-odbl-export
plan: 05
subsystem: ops
tags: [odbl, export, systemd, timer, github-actions, ssh, docker-compose, retention, deploy]

# Dependency graph
requires:
  - phase: 14-open-odbl-export
    plan: 02
    provides: letmegetin-admin export odbl --out DIR [--delta], latest.json, in-command retention
  - phase: 14-open-odbl-export
    plan: 03
    provides: the export_data volume mounted :ro at /data/export, LETMEGETIN_EXPORT_DIR, the proven /data/export-rw writable target
  - phase: 14-open-odbl-export
    plan: 04
    provides: the frozen public deltas contract (watermark, from_seq/to_seq, --since as catch-up)
provides:
  - scripts/export-odbl.sh {snapshot|delta} — one container writing the served volume at /data/export-rw
  - deploy/systemd/letmegetin-export-odbl-{snapshot,delta}.{service,timer}
  - .github/workflows/export-odbl.yml (workflow_dispatch, SSH, no DB/API secret)
  - docs/deploy.md "ODbL export" — unit contents, retention-is-automatic, atomic-import stance
affects: [phase 15 acceslibre destination]

actuals:
  tokens: 3522
  tasks: 3
  commits: 3
  plan_head_before: 213e638ca76b50943fbe68b00fe0f674a6e179a8
  plan_head_after: a10152c3aca57c8afa2496b39a8eda9e8372554b

tech-stack:
  added: []
  patterns:
    - "The one-off container mounts the served volume at /data/export-rw: compose appends `run -v` mounts, so the api's :ro entry always wins (proven in 14-03)"
    - "A timer per schedule when the difference is the command argument: two services, two timers, no conditional shell"
    - "The wrapper never reads latest.json; the export command owns the watermark under its own flock (D-10)"
    - "Actions carries only the SSH connection: the host fingerprint is a repository variable because a host key is public data"

key-files:
  created:
    - scripts/export-odbl.sh
    - deploy/systemd/letmegetin-export-odbl-snapshot.service
    - deploy/systemd/letmegetin-export-odbl-snapshot.timer
    - deploy/systemd/letmegetin-export-odbl-delta.service
    - deploy/systemd/letmegetin-export-odbl-delta.timer
    - .github/workflows/export-odbl.yml
    - tests/unit/scripts/test_export_odbl_wrapper.py
  modified:
    - docs/deploy.md

key-decisions:
  - "The wrapper mounts export_data at /data/export-rw and passes --out /data/export-rw: the plan's `-v export_data:/data/export` is silently ignored and the container gets a read-only filesystem (14-03 proved it live)."
  - "The host key fingerprint is a repository variable, not a secret: a host public key is public data, and an Actions secret would imply it is sensitive. Unset, the action does not verify — the runbook says so plainly."
  - "The delta branch is `--delta` with no `jq` and no `--since`; a unit test asserts a fake jq is never called, so the watermark cannot drift into the shell."
  - "Two timers, two services, mode as the ExecStart argument — a single timer with two OnCalendar lines would fire the same unit twice with no way to tell which run should snapshot."
  - "The workflow's mode is a `choice` input validated again on the host (`case`` before the wrapper), so an unexpected value cannot reach the CLI."
  - "RETENTION needs no unit: it runs inside `export odbl` after each snapshot (14-02), and `letmegetin-retention` is the unrelated token/idempotency job."

patterns-established:
  - "A host wrapper's test shims docker and the one tool it must not call (jq), then asserts the exact argv — the failure it exists to catch is invisible otherwise."

requirements-completed: [EXP-01]

coverage:
  - id: D1
    description: "scripts/export-odbl.sh builds the exact snapshot and delta argv against the writable /data/export-rw mount, with one OUT variable, no jq and no --since, and exits 2 with a usage line on an unknown mode"
    requirement: EXP-01
    verification:
      - kind: unit
        ref: "tests/unit/scripts/test_export_odbl_wrapper.py (3 tests: snapshot argv, delta argv + no jq/--since, unknown-mode exit 2)"
        status: pass
      - kind: other
        ref: "bash -n scripts/export-odbl.sh"
        status: pass
    human_judgment: false
  - id: D2
    description: "A weekly snapshot (Mon 04:00) and a daily delta (03:15) run as four units with distinct ExecStart arguments, through with-secrets.sh, with no secret baked in"
    requirement: EXP-01
    verification:
      - kind: other
        ref: "each of the four units is non-empty and carries ExecStart= / OnCalendar="
        status: pass
    human_judgment: true
    rationale: "systemd-analyze verify cannot run on the macOS workstation this plan executed on; the units are a structural copy of letmegetin-retention.service, but a Linux host must confirm they load."
  - id: D3
    description: "The workflow is workflow_dispatch only, SSHes to the host and runs the wrapper with the chosen mode, and carries no database credential or API secret"
    requirement: EXP-01
    verification:
      - kind: other
        ref: "PyYAML parses .github/workflows/export-odbl.yml; grep shows only DEPLOY_HOST/DEPLOY_USER/DEPLOY_SSH_KEY secrets and the DEPLOY_HOST_FINGERPRINT variable"
        status: pass
    human_judgment: true
    rationale: "The SSH placeholders are filled by the operator when the host exists; nothing in CI can prove the connection works before that."
  - id: D4
    description: "docs/deploy.md states the volume and LETMEGETIN_EXPORT_DIR, the read-only/read-write split, the exact unit lines, the MVCC delta, the Actions prerequisite with the runner-IP allowlist, automatic retention, and the atomic import"
    requirement: EXP-01
    verification:
      - kind: other
        ref: "python assertion over docs/deploy.md (export-odbl.sh, both OnCalendar lines, ExecStart=, workflow_dispatch, watermark, DEPLOY_*, run --rm -T -v export_data:/data/export, atomic)"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-11-14
status: complete
---

# Phase 14 Plan 05: Host generation, timers and the on-demand run Summary

**The export now runs itself on the host: `scripts/export-odbl.sh {snapshot|delta}` wraps one container writing the served volume at `/data/export-rw`, a weekly snapshot and a daily delta are four systemd units with the mode as the argument, and a `workflow_dispatch` SSHes in to run the same wrapper — with no database or API secret anywhere in Actions.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified/created:** 8 (7 created, 1 modified)
- **Commits:** 3 measured (`git rev-list --count 213e638..HEAD` before this file)

## Accomplishments

- **The wrapper is three branches and one variable.** `OUT=${EXPORT_DIR_IN_CONTAINER:-/data/export-rw}` is defined once, before the `case`, so `set -u` never sees an undefined variable in either mode. `snapshot` and `delta` differ by one token; anything else prints `usage: export-odbl.sh {snapshot|delta}` to stderr and exits 2.
- **The mount target is the one the previous plan proved.** The argv is exactly
  `compose -p letmegetin-prod -f docker-compose.prod.yml run --rm -T -v export_data:/data/export-rw api letmegetin-admin export odbl --out /data/export-rw [--delta]`.
  `--delta` is on the delta branch only; the wrapper never opens `latest.json`.
- **The test proves the argv, not docker.** A fake `docker` writes its arguments to a temp file; a fake `jq` writes a marker and exits 1. Both modes run under `bash -u` and are asserted argument-for-argument (`export_data:/data/export-rw`, `--out /data/export-rw`, `--delta` only in delta mode), plus "no `--since`", "no `cat`/`jq`", "jq never called", and the unknown-mode exit 2 with an empty argv.
- **Four units, two schedules.** `letmegetin-export-odbl-snapshot.{service,timer}` (`OnCalendar=Mon *-*-* 04:00:00`) and `letmegetin-export-odbl-delta.{service,timer}` (`OnCalendar=*-*-* 03:15:00`), each service `Type=oneshot` with `WorkingDirectory=/opt/letmegetin` and `EnvironmentFile=/etc/letmegetin/infisical.env`, each `ExecStart` going through `with-secrets.sh`.
- **The workflow carries only the SSH connection.** `workflow_dispatch` with a `delta`/`snapshot` `choice`; `appleboy/ssh-action` pinned to `0ff4204d…` (v1.2.5), `host`/`username`/`key` from the three `DEPLOY_*` secrets, the host key fingerprint from a repository variable, a 2 h command timeout (the 10 m default cannot stream a full snapshot), and a remote `case` re-check before the wrapper sees the mode.
- **The runbook stays one section.** `## ODbL export` in `docs/deploy.md` was extended, not duplicated: volume and `LETMEGETIN_EXPORT_DIR`, the `:ro` / `-rw` split with the command that does the writing, a table of the two timers with their real `OnCalendar` and `ExecStart` lines, the enable command, the MVCC delta versus `--since`, the Actions prerequisite including the runner-IP allowlist, and the two operational facts a reader would otherwise re-derive: retention is automatic inside the export, and the AccesLibre import is untouched and atomic.

## Task Commits

Each task was committed atomically:

1. **Task 1: `scripts/export-odbl.sh` + argv test** — `053fe3e` (feat)
2. **Task 2: four systemd units + workflow_dispatch** — `29b31ca` (feat)
3. **Task 3: `docs/deploy.md` export operations** — `a10152c` (docs)

**Plan metadata:** committed separately after this file.

## Verification (real output)

| Command | Result |
|---|---|
| `bash -n scripts/export-odbl.sh` | exit 0 |
| `uv run pytest tests/unit/scripts/test_export_odbl_wrapper.py -m unit -x -q` | **3 passed** in 0.28 s |
| `uv run python -c "import yaml … safe_load(.github/workflows/export-odbl.yml)"` | `yaml ok` |
| four-unit check (`test -s` + `grep ExecStart=\|OnCalendar=`) | all four `ok` |
| compose assertion (api volumes `export_data:/data/export:ro`, `LETMEGETIN_EXPORT_DIR == /data/export`, named volume declared) | `compose ok: ['export_data:/data/export:ro']` |
| docs assertion (plan's Task-3 python snippet) | `ok` |
| `uv run pytest -q` | **484 passed**, 1 third-party `httpx` warning in 134 s (481 before this plan) |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `166 files already formatted` |
| `node .gitnexus/run.cjs detect-changes --scope all` | "Diff touched 2 file(s) but no indexed symbols overlap those hunks" — shell/YAML/Markdown are outside the graph; the only Python file is a new test |
| mutation check on the argv assertion | running the wrapper with `EXPORT_DIR_IN_CONTAINER=/data/export` records `… -v export_data:/data/export … --out /data/export`, i.e. the plan's original shape fails the test |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The planned read-write mount is silently ignored, so generation would fail**
- **Found during:** Task 1, before writing the wrapper
- **Issue:** The plan's `compose run --rm -T -v export_data:/data/export api … --out /data/export` does not override the api service's `export_data:/data/export:ro`. Compose **appends** `run -v` mounts, and the read-only entry wins, so the one-off container would die with `Read-only file system` on the first production run. Plan 14-03 had already proven this live and flagged it for this plan.
- **Fix:** the wrapper mounts the same volume at `/data/export-rw` and passes `--out /data/export-rw`; the plan's Task-1 text and its argv assertions were updated to match. No `!override` overlay was introduced (pre-commit's `check-yaml` rejects the tag — see 14-03).
- **Files modified:** `scripts/export-odbl.sh`, `tests/unit/scripts/test_export_odbl_wrapper.py`
- **Verification:** the unit test asserts `-v export_data:/data/export-rw` and `--out /data/export-rw`; the mutation check above shows the old shape fails it.
- **Committed in:** `053fe3e`

**2. [Rule 2 - Missing critical functionality] The SSH step did not verify the host key**
- **Found during:** Task 2 (workflow review against `docs/rules/deploy.md`)
- **Issue:** `appleboy/ssh-action` accepts any host key unless `fingerprint` is given, and the rules require host keys verified ("Host keys verified … Do not disable it to get a deploy through"). The plan named only three placeholders and said nothing about the host key.
- **Fix:** added `fingerprint: ${{ vars.DEPLOY_HOST_FINGERPRINT }}` as a repository **variable** (a host public key is public data, so it is not a secret), documented as the fourth prerequisite, and stated honestly that an unset variable means no verification. When unset this behaves exactly like the plan's version, so it adds no failure mode.
- **Files modified:** `.github/workflows/export-odbl.yml`, `docs/deploy.md`
- **Verification:** workflow parses; `gitleaks` passed on the commit.
- **Committed in:** `29b31ca` (workflow), `a10152c` (docs)

### Plan adjustments (documented, not defects)

**3.** The plan's Task 3 said "add an `ODbL export` section under Operations"; per 14-03's and 14-04's handoff the section already existed and was **extended in place** — a second export section would have drifted immediately.
**4.** The timers carry an explicit `Unit=` line naming their service. The existing timers rely on name matching; making it explicit costs one line and states which mode each calendar fires.
**5.** `--delta` follows `--out` in the delta argv (`export odbl --out "$OUT" --delta`) rather than the plan's `--out "$OUT" --delta` ordering being left implicit — Typer accepts either; the test pins the shipped order.
**6.** The workflow's `command_timeout` is 2 h, not the action's 10 m default: a snapshot streams ~1.7 M answer rows and would be killed mid-write, which is the one failure mode this run must not improvise around.
**7.** `DEPLOY_HOST_FINGERPRINT` is the only name not in the plan or the parent brief; see deviation 2.

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 2) + 5 documented plan adjustments.
**Impact on plan:** the generation command's mount target is the only behavioural change, and it is the one the previous plan had already found and proven; everything else is naming, explicitness and one hardening option that defaults to the plan's behaviour.

## Threat Flags

None new. T-14-13 (Actions → host) is mitigated by what this plan ships: `workflow_dispatch` only, no DB/API secret in Actions, a pinned action SHA, an optional host-key fingerprint, a `choice` input re-validated on the host, and the runner-IP allowlist documented as a prerequisite. T-14-14 (the mode argument) is mitigated by the `case` in the wrapper plus the argv test. T-14-15 did not fire: no package was added.

## Known Stubs

None. Every unit, the workflow and the doc describe commands that exist at this commit.

## Issues Encountered

- `git rev-list --count 213e638..HEAD` was measured before the summary commit; the number in the frontmatter (3) is the three task commits.
- The pre-commit wrapper stashed the pre-existing dirty `.planning/STATE.md` / `.planning/state.json` on every commit and restored them; neither was staged or committed by this plan, and both files were left untouched as instructed.
- `systemd-analyze verify` is unavailable on macOS, so unit validity is a structural comparison with `letmegetin-retention.service`, not an execution. A Linux host should run it once.

## User Setup Required

On the host:

1. `systemctl enable --now letmegetin-export-odbl-snapshot.timer letmegetin-export-odbl-delta.timer` (after copying `deploy/systemd/` there, as with the other units).
2. In GitHub: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` secrets and the `DEPLOY_HOST_FINGERPRINT` variable before the first `workflow_dispatch`.
3. Open the firewall to the Actions runner IP for the run and close it after.

## Next Phase Readiness

- **The first snapshot is the journal baseline** (D-09): until `export-odbl.sh snapshot` runs once on the host, `latest.json` does not exist and a delta fails loudly rather than inventing a baseline — the correct order is snapshot then delta.
- **Phase 15 (AccesLibre destination)** adds no unit: the same two timers cover any new ZIP, because the export command writes every archive and owns `latest.json`.
- **A second host would need its own lock**: `flock` on `latest.json` serialises one filesystem. The D-12 design assumes one generating host; a second would need a shared lock, not a second timer.

---

## Self-Check: PASSED

- Files exist: `scripts/export-odbl.sh`, the four `deploy/systemd/letmegetin-export-odbl-*` units, `.github/workflows/export-odbl.yml`, `tests/unit/scripts/test_export_odbl_wrapper.py`, `docs/deploy.md` — found.
- Commits reachable from HEAD: `053fe3e`, `29b31ca`, `a10152c` — found.
- Verification re-run at HEAD: wrapper test 3 passed, workflow YAML parses, four units non-empty with their lines, compose assertion holds, docs assertion holds, full suite 484 passed, `ruff check` and `ruff format --check` clean.
