---
phase: 14-open-odbl-export
plan: 03
subsystem: api
tags: [odbl, export, fastapi, read-only, path-traversal, docker-compose, volume, openapi]

# Dependency graph
requires:
  - phase: 14-open-odbl-export
    plan: 02
    provides: latest.json and the snapshot/delta/catch-up ZIPs written under flock
  - phase: 10-authenticated-api (public_rate_limit, api/deps.py)
    provides: the anonymous per-IP rate limiter shared by every public read
provides:
  - GET /api/v1/export/latest.json (CLI-written index, 404 when absent)
  - GET /api/v1/export/{name}.zip (plain .zip name only, resolved under export_dir)
  - settings.export_dir (LETMEGETIN_EXPORT_DIR, default /data/export)
  - export_data named volume mounted read-only at /data/export in the api service
  - the documented read-write generation mount (second, writable target)
affects: [14-04 public-api docs, 14-05 export wrapper/timer]

actuals:
  tokens: 3719
  tasks: 2
  commits: 2
  plan_head_before: bcac2e0886c3832b6e1ec6a364462d934a2eca29
  plan_head_after: b9c5ef3ced21f125f8b90aeb4387df49012d1bc3

tech-stack:
  added: []
  patterns:
    - "A served file name is validated before any filesystem access, then re-checked by resolved-path containment after it"
    - "Compose appends `run -v` mounts to a service's own list: a `:ro` service mount cannot be relaxed by the run flag, so the writer mounts the same volume at a second, writable target"
    - "One 404 for every unusable export request: missing file, unreadable index, bad name, escape attempt — the caller learns nothing about which archives exist"

key-files:
  created:
    - src/letmegetin/api/v1/export.py
    - tests/functional/api/test_export.py
  modified:
    - src/letmegetin/config.py
    - src/letmegetin/api/v1/router.py
    - src/letmegetin/main.py
    - docker-compose.prod.yml
    - docs/deploy.md
    - docs/openapi.json

key-decisions:
  - "Every rejection is 404, never 422: a bad name, a missing archive and an escape attempt are indistinguishable, so the route is not an oracle for the directory's contents (the plan said 422 for a bad name)."
  - "settings.export_dir defaults to /data/export, the compose path, so the setting and the volume mount are one path in two surfaces (the plan said data/export)."
  - "There is no 503: the setting always has a value, so an unprovisioned deployment reads as 404 and the route description says so."
  - "Traversal defence is two-layered: `_is_servable` rejects separators, `..`, dotfiles, .lock and .tmp before any filesystem call, then `resolve()` + `is_relative_to` catches a symlink planted inside the directory."
  - "No compose overlay using `!override`: pre-commit's check-yaml cannot parse the tag. The generation mounts the same volume at /data/export-rw instead, which needs no new file and no gate change."
  - "The export tag is declared in main.py's openapi_tags so /docs names the section instead of showing a bare tag."

requirements-completed: [EXP-01]

coverage:
  - id: D1
    description: "GET /api/v1/export/latest.json serves the CLI-written index under the anonymous rate limit, and 404s when no export has been written"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "tests/functional/api/test_export.py#test_latest_json_serves_the_index_the_cli_wrote; #test_latest_json_is_404_before_the_first_export; #test_latest_json_is_404_when_the_index_is_unreadable"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /api/v1/export/{name}.zip serves an archive from export_dir and no name can escape it (separators, .., encoded separators, absolute, symlink, lock, temp)"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "test_zip_serves_the_archive_with_the_zip_media_type; test_a_traversal_name_never_escapes_the_export_directory (9 cases); test_a_symlink_out_of_the_directory_is_not_served; test_only_a_plain_zip_name_is_servable"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both export routes run behind the anonymous public_rate_limit (429 proven, not introspected)"
    requirement: EXP-01
    verification:
      - kind: functional
        ref: "test_both_export_routes_stay_under_the_anonymous_rate_limit"
        status: pass
    human_judgment: false
  - id: D4
    description: "The export_data volume is mounted into api read-only at LETMEGETIN_EXPORT_DIR and declared as a named volume"
    requirement: EXP-01
    verification:
      - kind: other
        ref: "yaml assertion on docker-compose.prod.yml; `docker compose config` shows read_only: true; live `docker compose run` proof that the :ro target is unwritable"
        status: pass
    human_judgment: false

# Metrics
duration: 35min
completed: 2026-11-14
status: complete
---

# Phase 14 Plan 03: Read-only export serving and the export volume Summary

**`GET /api/v1/export/latest.json` and `GET /api/v1/export/{name}.zip` now serve the CLI-written export under the anonymous quota from `LETMEGETIN_EXPORT_DIR`, with a name guard plus resolved-path containment that no traversal case gets through — and the `export_data` volume is mounted read-only into `api`, with the writable generation mount documented and proven.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2
- **Files modified/created:** 8 (2 created, 6 modified)
- **Commits:** 2 measured (`git rev-list --count bcac2e0..HEAD` before the summary commit)

## Accomplishments

- **Two read routes, no generation.** `src/letmegetin/api/v1/export.py` carries the router with
  `dependencies=[Depends(public_rate_limit)]`; `latest.json` is read and returned as JSON with
  `Cache-Control: public, max-age=300`, an archive is returned by `FileResponse` with
  `application/zip` and `max-age=3600`. Neither route writes, and neither ever builds a ZIP.
- **The traversal guard is exercised for real.** Nine bad URLs (`../ secret.txt`, `..%2F`,
  `%2e%2e%2F`, `%2Fetc%2Fpasswd.zip`, `a/b.zip`, `x.txt`, `..`, `latest.json.lock`,
  `.export-….zip.tmp`) each return 404/422 and none contains the marker of a `secret.txt` planted
  outside the directory. A symlink `leak.zip` inside the directory pointing at that secret is
  refused by the `resolve()`/`is_relative_to` layer, which is the case a name-only guard would miss.
- **404, never 503.** The setting always has a value, so "not provisioned" and "not generated yet"
  collapse into one answer; the OpenAPI description states it in as many words.
- **The limiter is proven, not assumed.** With `rate_limit_default_rpm = 1`, each route answers
  200 then 429 in the same test, so both carry the anonymous quota.
- **The volume is wired and the split is real.** `export_data` is declared, mounted
  `export_data:/data/export:ro` in `api`, and `LETMEGETIN_EXPORT_DIR: /data/export` sits beside it.
  `docker compose config` renders `read_only: true`; a throwaway `docker compose run` against a copy
  of the same shape proved the `:ro` target cannot be written (see Deviations 1).
- **OpenAPI is regenerated and byte-stable.** Both operations carry a summary and a description, the
  `export` tag is declared, and two consecutive runs of `scripts/export_openapi.py` produce the same
  SHA-256.

## Task Commits

1. **Task 1: Read-only export routes + export_dir setting** — `8163e81` (feat)
2. **Task 2: export_data volume + LETMEGETIN_EXPORT_DIR env** — `b9c5ef3` (chore)

**Plan metadata:** the summary commit follows this file.

## Verification (real output)

| Command | Result |
|---|---|
| `uv run pytest tests/functional/api/test_export.py -m functional -x` | **27 passed**, 1 third-party `httpx` deprecation warning (5.7 s) |
| `uv run pytest -q` (whole suite) | **480 passed**, 1 warning (137 s); 453 before this plan |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `165 files already formatted` |
| `uv run mypy` | `Success: no issues found in 87 source files` |
| `uv run bandit -r src -c pyproject.toml` | `Total issues: 0` (Low 0, Medium 0, High 0) |
| compose assertion (YAML + `:ro` + env + named volume, no service added) | `ok` |
| `docker compose -f docker-compose.prod.yml config` | api renders `source: export_data`, `target: /data/export`, `read_only: true` |
| `uv run python scripts/export_openapi.py` twice, `shasum` | `0ae5a1ba…` both runs — deterministic |
| `node .gitnexus/run.cjs analyze --index-only` (index was stale at `107c7ef`) | 3 841 nodes, 7 570 edges |
| `node .gitnexus/run.cjs detect-changes --scope all` (pre-commit) | 6 files, 3 symbols, `Risk level: low`, 0 affected processes |

The `docker compose run` proof (throwaway project, same mount shape):

```
$ docker compose run --rm -v export_data:/data/export x sh -c 'echo rw-ok > /data/export/probe'
sh: can't create /data/export/probe: Read-only file system            # the run -v does NOT relax :ro
$ docker compose run --rm -v export_data:/data/export-rw x sh -c 'echo rw-ok > /data/export-rw/probe'
rw-ok                                                                  # second target, same volume, writable
```

## Decisions Made

- **One 404 for every unusable request.** The plan asked for 422 on a bad name and 404 on a missing
  file; the two answers would tell a probe which names are real. Every failure is 404 with the same
  detail, and the test asserts `in (400, 404, 422)` so it stays true if that ever changes.
- **Default `/data/export`, not the plan's `data/export`.** One path in two surfaces: the compose
  mount and the setting cannot drift, and a development machine gets a clean 404 instead of a
  directory next to the checkout.
- **A writable second target beats an overlay file.** Compose appends `run -v` mounts, so
  `-v export_data:/data/export` is ignored in favour of the service's `:ro` entry. `!override` fixes
  that but pre-commit's `check-yaml` rejects the tag (PyYAML has no constructor); excluding the file
  from the YAML gate would weaken a gate to accommodate a plugin, so the documented command mounts
  the same volume at `/data/export-rw` and passes `--out /data/export-rw`.
- **The tag description lives in `main.py`.** `openapi_tags` is where the other four tags are
  described; leaving `export` undeclared would have shipped a bare section in `/docs`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] A compose overlay with `!override` cannot pass the commit hooks**
- **Found during:** Task 2 commit
- **Issue:** `docker compose run -v export_data:/data/export api …` does not relax the service's
  read-only mount (proven live: `Read-only file system`). The working fix, an overlay file using
  `volumes: !override`, was rejected by pre-commit's `check-yaml`
  (`could not determine a constructor for the tag '!override'`), and the alternatives were to
  exclude a YAML file from the YAML gate or to weaken the mount.
- **Fix:** dropped the overlay; the documented generation command mounts the same named volume at a
  second, writable target (`/data/export-rw`) and points `--out` at it — verified live with the same
  compose mechanics, and no gate was touched.
- **Files modified:** `docker-compose.prod.yml`, `docs/deploy.md`
- **Verification:** YAML assertion `ok`; `docker compose config` renders the read-only mount; the
  throwaway run wrote through `/data/export-rw` and read the file back through `/data/export:ro`.
- **Committed in:** `b9c5ef3`

### Plan adjustments (documented, not defects)

**2.** The `{name}` guard answers **404**, not the plan's 422 (see Decisions).
**3.** `settings.export_dir` defaults to **`/data/export`**, not the plan's `data/export` (see Decisions).
**4.** The plan's Task-2 verify snippet assumed `services.api.environment` is a list; this compose file
has always used the mapping form, so the equivalent assertion reads
`v["environment"]["LETMEGETIN_EXPORT_DIR"] == "/data/export"`. Same truth, correct shape.
**5.** `src/letmegetin/main.py` (the `export` openapi tag) and `docs/openapi.json` are not in the
plan's `files_modified`; both are required for the OpenAPI contract the parent task asked for.
**6.** The traversal test list is longer than the plan's six names (nine, plus a symlink case and a
helper-level parametrisation): the URL layer normalises some of them before the handler sees them, so
the helper-level test is what exercises the guard with the raw strings.

---

**Total deviations:** 1 auto-fixed (blocking) + 5 documented plan adjustments.
**Impact on plan:** no requirement lost; the generation mount mechanism and the status code are the
two shapes that changed, both for reasons verified in this session.

## Threat Flags

None new. T-14-07 is implemented and tested at both layers described above (name guard before any
filesystem access, resolved-path containment after it). T-14-08 holds: the served directory carries
only export files, and the routes expose no path into the rest of the filesystem. No secret, no Caddy
change, no write path from the API process (the volume is `:ro`).

## Known Stubs

None.

## Issues Encountered

- **Compose mount precedence is counter-intuitive and silent.** `docker compose run -v <vol>:<target>`
  appends to the service's list; when the target repeats, the service's entry wins — a read-write
  override therefore does nothing unless it uses a different target or `!override`. The first
  `docker compose run` attempt in this session failed with `Read-only file system`, which is exactly
  what plan 14-05's sketched command would have done in production.
- pre-commit's `check-yaml` is PyYAML-based and rejects Compose's `!override` / `!reset` tags.

## Next Phase Readiness

- **14-04 (public contract):** the two routes are `/api/v1/export/latest.json` and
  `/api/v1/export/{name}.zip`; both answer 404 (never 503) when there is nothing to serve, carry
  `Cache-Control: public, max-age=300` / `max-age=3600`, and sit under the anonymous per-IP limit.
  `docs/openapi.json` is regenerated and stable; `application/places/attribution.py` still exposes
  `PRODUCED_WORKS_SENTENCE` / `FORWARD_LOOKING_SENTENCE` for a docs test to import.
- **14-05 (wrapper/timer):** **the planned `docker compose run --rm -T -v export_data:/data/export api`
  does not work** — the api service mounts that path `:ro` and compose appends rather than replaces,
  so the generation container gets a read-only filesystem. Use
  `-v export_data:/data/export-rw api letmegetin-admin export odbl --out /data/export-rw` (proven
  here), or re-introduce an `!override` overlay and exempt it from `check-yaml`. The volume resolves
  as `letmegetin-prod_export_data` under the `-p letmegetin-prod` project.
- **14-05 also owns `docs/deploy.md`:** an `## ODbL export` section already states the volume, the
  setting, the read-only/read-write split and the manual command — extend it with the timer and the
  Actions trigger instead of adding a second, competing section.

---

## Self-Check: PASSED

- Files exist: `src/letmegetin/api/v1/export.py`, `tests/functional/api/test_export.py` — found.
- Commits reachable from HEAD: `8163e81`, `b9c5ef3` — found.
- Plan verification re-run at HEAD: functional 27 passed, full suite 480 passed, `ruff check` /
  `ruff format --check` clean, `mypy` clean, compose YAML assertion `ok`, OpenAPI deterministic.
