---
phase: 15-acceslibre-round-trip
plan: 02
subsystem: api
tags: [httpx, acceslibre, domain-pure, ports, push-diff]

# Dependency graph
requires:
  - phase: 15-acceslibre-round-trip
    provides: the phase's locked decisions D-10/D-11 and the plan 15-01 export groundwork
  - phase: 12-licence-provenance
    provides: the `_rejection` freshness intent this plan re-expresses as a named push rule
provides:
  - a fixed-origin AccesLibre HTTP adapter (get_erp / patch_erp / list_erps) behind a domain port
  - a pure push decision (typed diff, amended-D-11 freshness, strict value validation, PATCH payload)
  - `resolve_identifier`, the single place the probe's identifier rule becomes a key
  - `AccesLibrePort` and `AccesLibrePushRepositoryPort` domain ports
  - `httpx` as a runtime dependency and the `acceslibre_api_key` setting
affects: [15-03-probe, 15-04-lov2-feed, 15-05-push-use-case, 15-06-journal]

actuals:
  tokens: 7174
  tasks: 2
  commits: 2
plan_head_before: 2f82b7f9d466c57cbe751399889b49bb78635abf
plan_head_after: 9e6a41abdc50cb7aaf669940d34b234e9d81065c

tech-stack:
  added: []
  patterns:
    - "infrastructure adapter behind a domain Protocol, so `application/` never imports httpx"
    - "one pure module owns the diff/freshness/validation rules; the adapter only transports"

key-files:
  created:
    - src/letmegetin/infrastructure/acceslibre/client.py
    - src/letmegetin/domain/places/acceslibre_push.py
    - tests/integration/acceslibre/fakes.py
    - tests/integration/acceslibre/test_client.py
    - tests/unit/infrastructure/acceslibre/test_client_security.py
    - tests/unit/domain/places/test_acceslibre_push.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/letmegetin/config.py

key-decisions:
  - "The adapter sends booleans as the strings \"true\"/\"false\": the live write schema declares `type: string`, not a JSON boolean (Pitfall 9), while the read side returns real booleans."
  - "The write schema's enum and integer bounds were pinned from the live OpenAPI (2026-11-15): entree_porte_manoeuvre ∈ {battante, coulissante, tourniquet, tambour}, entree_marches / entree_largeur_mini ∈ 0..32767."
  - "Three bounded attempts on 429/5xx, honouring Retry-After seconds else a 1 s pause; a 401/403 raises on the first response, because a retry cannot fix an auth or permission answer."
  - "freshness_decision ties go to us (`claim >= theirs`), an undated remote value never blocks a push, and a missing claim date always skips — we never overwrite without a date."

patterns-established:
  - "Protocol in domain, httpx in infrastructure: the adapter is the only module that imports httpx."
  - "The module that decides also rejects: an unknown value raises DomainError rather than being coerced, so a mapping gap surfaces as a failure instead of a silent null."

requirements-completed: [PART-02]

coverage:
  - id: D1
    description: "Fixed-origin AccesLibre adapter: Api-Key auth, TLS on, no redirects, bounded 429 retry, key never in a message"
    requirement: PART-02
    verification:
      - kind: unit
        ref: "tests/unit/infrastructure/acceslibre/test_client_security.py"
        status: pass
      - kind: integration
        ref: "tests/integration/acceslibre/test_client.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pure push decision: typed diff, amended-D-11 freshness (observed_at else recorded_at), strict value validation, accessibilite payload without user_id"
    requirement: PART-02
    verification:
      - kind: unit
        ref: "tests/unit/domain/places/test_acceslibre_push.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "resolve_identifier maps the probe's rule to a key and returns None under blocked/slug-without-slug; the two domain ports are declared"
    requirement: PART-02
    verification:
      - kind: unit
        ref: "tests/unit/domain/places/test_acceslibre_push.py#test_resolve_identifier_follows_the_recorded_rule"
        status: pass
    human_judgment: false
  - id: D4
    description: "httpx is a runtime dependency and LETMEGETIN_ACCESLIBRE_API_KEY exists with no origin setting"
    requirement: PART-02
    verification:
      - kind: other
        ref: "uv lock --check"
        status: pass
      - kind: unit
        ref: "tests/unit/infrastructure/acceslibre/test_client_security.py#test_the_only_acceslibre_setting_is_the_key"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-11-15
status: complete
---

# Phase 15 Plan 02: AccesLibre outbound adapter and pure push decision Summary

**A fixed-origin httpx adapter that cannot leak the partner key, plus a pure typed-diff/freshness decision that reads `observed_at`-else-`recorded_at` so a community answer can actually win**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-15T18:12:37Z
- **Completed:** 2026-11-15T18:16:30Z
- **Tasks:** 2
- **Files modified:** 11 (2 empty package markers)

## Accomplishments

- `httpx` moved from the dev group to `[project] dependencies`; `uv lock` regenerated, `uv lock --check` green.
- `LETMEGETIN_ACCESLIBRE_API_KEY` added to settings — and nothing else: the origin is a module constant, pinned by a test that fails if any other `acceslibre_*` setting appears.
- `AccesLibreClient` speaks only to `https://acceslibre.beta.gouv.fr`, sends `Authorization: Api-Key <key>`, keeps `verify=True` / `follow_redirects=False`, retries 429/5xx a bounded three times honouring `Retry-After`, and carries slug + status — never the key — in every error.
- `domain/places/acceslibre_push.py` holds the whole push decision: typed normalisation of both sides, `diff_fields`, `freshness_decision` per amended D-11, `validate_value` (reject, never coerce), `push_payload` nested under `accessibilite`, `resolve_identifier`, and the `AccesLibrePort` / `AccesLibrePushRepositoryPort` Protocols.
- 36 unit tests + 12 stub-backed integration tests, no socket and no database touched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Promote httpx, add the key setting, build the fixed-origin adapter** - `bce404b` (feat)
2. **Task 2: The pure push decision, the identifier resolver, the domain ports** - `9e6a41a` (feat)

**Plan metadata:** recorded by the close-out commit (docs).

## Files Created/Modified

- `src/letmegetin/infrastructure/acceslibre/client.py` — the adapter: constant origin, Api-Key header, bounded retry, redacted errors.
- `src/letmegetin/domain/places/acceslibre_push.py` — the pure decision module and the two ports.
- `src/letmegetin/config.py` — `acceslibre_api_key: str | None`.
- `pyproject.toml` / `uv.lock` — httpx promoted to runtime, lock regenerated.
- `tests/integration/acceslibre/{__init__,fakes,test_client}.py` — one shared `MockTransport` stub, 12 tests.
- `tests/unit/infrastructure/acceslibre/test_client_security.py` — origin constant, TLS on, no redirects, key absent from errors, no host setting.
- `tests/unit/domain/places/test_acceslibre_push.py` — 36 tests over the decision module.

## Decisions Made

- **Booleans travel as the strings `"true"`/`"false"`.** The live write schema declares them `type: string` (verified in the fetched OpenAPI, 2026-11-15); their `NullBooleanField` accepts both forms, and the declared contract is the safer of the two.
- **The enum and integer bounds are pinned from the live schema**, not guessed: `entree_porte_manoeuvre` ∈ {battante, coulissante, tourniquet, tambour}; `entree_marches` / `entree_largeur_mini` ∈ 0..32767. A value outside them raises, so a mapping gap becomes a visible failure instead of a silent `null`.
- **`normalise` accepts our web form's `oui`/`non`** because that is what the contribution form stores for a boolean criterion; anything else is rejected.
- **Retry policy:** three attempts on 429/5xx, `Retry-After` seconds honoured, otherwise a 1 s pause; 401/403 raise on the first response (a retry cannot fix an auth or permission answer).
- **Freshness ties go to us; an undated remote value never blocks; a missing claim date always skips** — we never overwrite their value without a date of our own.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `src/letmegetin/infrastructure/acceslibre/__init__.py`**
- **Found during:** Task 1 (the adapter)
- **Issue:** `files_modified` lists `client.py` only, but `infrastructure/acceslibre/` needs a package marker beside `persistence/`.
- **Fix:** empty `__init__.py`, matching the existing `infrastructure/persistence/__init__.py`.
- **Verification:** imports resolve; `uv run mypy` clean over 90 source files.
- **Committed in:** `bce404b`

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** none beyond the package marker; no scope creep, no new dependency.

## Issues Encountered

- **GitNexus index is 44 commits behind HEAD** (`lastCommit 64d2b27`, HEAD `2f82b7f`). `impact Settings` reported HIGH with 15 direct callers — an artefact of caller count, not of this change: the field added is defaulted, so no caller breaks; mypy and the full unit+integration run confirm it. `detect_changes` reported the config change for Task 1 and "none" for Task 2 because the new module is still untracked (it indexes files, not additions). No reindex was run; grep and the test suite were used to confirm.
- **`normalise` / `validate_value` share one implementation** (`_typed`) with the plan's two signatures kept: the read-side comparison and the write-side egress check must not drift, and duplicating the type table would have been the drift.
- The `starlette.testclient` deprecation warning in the suite is pre-existing and unrelated.

## User Setup Required

None for this plan. The key itself (`LETMEGETIN_ACCESLIBRE_API_KEY`) belongs in the Infisical project `39c0bbf4-…` at `prod /` when it exists; no test reads it and nothing was printed.

## Next Phase Readiness

- 15-03 (probe) can import `AccesLibreClient` and call `list_erps(**filters)` / `get_erp(slug)`; it records the rule that `resolve_identifier` consumes.
- 15-04 (feed) and 15-05 (push) depend only on domain ports; the SQLAlchemy repository for `stream_owned_answers` / `append` is 15-05/15-06 work.
- Open: the real enum values our referential stores for `entree-ouverture-de-porte` may not match their enum — the mapping document (15-04) is where that gap is named; until then `validate_value` refuses rather than sends.

## Self-Check: PASSED
