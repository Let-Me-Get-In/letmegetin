---
phase: 14-open-odbl-export
plan: 04
subsystem: docs
tags: [odbl, export, public-api, openapi, attribution, mvcc, csv-guard]

# Dependency graph
requires:
  - phase: 14-open-odbl-export
    plan: 02
    provides: the seven frozen ZIP entry names, manifest keys, latest.json shape, attribution constants
  - phase: 14-open-odbl-export
    plan: 03
    provides: the two read-only routes and the regenerated OpenAPI schema
provides:
  - docs/public-api.md "ODbL export" contract (endpoints, per-file schema, origin ids, delta contract, CSV guard, attribution, Produced Works)
  - docs/openapi.json declaring application/zip for the archive route
  - a test pinning the shared attribution constants into the partner document
affects: [14-05 export wrapper/timer]

actuals:
  tokens: 3832
  tasks: 1
  commits: 1
  plan_head_before: 64d2b27e56948d5aad8fe32e7a4d9f711a7dc335
  plan_head_after: 07580f3

tech-stack:
  added: []
  patterns:
    - "The partner document quotes the application constant, and the test imports the constant; one string, two readers"
    - "A generated schema's media type is fixed at the route decorator, never in docs/openapi.json"

key-files:
  created: []
  modified:
    - docs/public-api.md
    - docs/openapi.json
    - tests/integration/api/test_openapi.py
    - src/letmegetin/api/v1/export.py

key-decisions:
  - "The CSV-guard allow-list is documented from FREE_TEXT_COLUMNS, not from the plan's shorthand: categories guards name+label and criteria guards label, but label is JSON and cannot start with =, +, - or @, so the guard is a no-op there."
  - "The ZIP route's media type is declared in the decorator (`response_class=FileResponse` plus a 200 application/zip response); docs/openapi.json is regenerated, never edited."
  - "The doc states the delta as one MVCC window and `--since` as the cumulative catch-up, so no reader can mistake a delta for a re-send."
  - "The closing licence paragraph now points at ATTRIBUTION.txt instead of naming OSM and Overture, which are not in today's export (D-05)."

patterns-established: []

requirements-completed: [EXP-02]

coverage:
  - id: D1
    description: "docs/public-api.md documents both export endpoints, the seven entries and their columns, the per-file origin ids, the MVCC delta contract, the CSV guard allow-list and the attribution rules; docs/openapi.json carries both paths"
    requirement: EXP-02
    verification:
      - kind: integration
        ref: "tests/integration/api/test_openapi.py#test_openapi_exposes_the_public_contract"
        status: pass
      - kind: integration
        ref: "tests/integration/api/test_openapi.py#test_public_api_documents_the_shared_attribution_sentences"
        status: pass
    human_judgment: false
  - id: D2
    description: "The Produced Works and forward-looking sentences in docs/public-api.md are the shared application constants, byte-identical to ATTRIBUTION.txt"
    requirement: EXP-02
    verification:
      - kind: integration
        ref: "import PRODUCED_WORKS_SENTENCE / FORWARD_LOOKING_SENTENCE and assert each in docs/public-api.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "The prose is a faithful contract: the delta is one window applied in order, a delta is never cumulative, --since is the catch-up refused below the floor, and attribution lists only sources present in the ZIP"
    requirement: EXP-02
    verification: []
    human_judgment: true
    rationale: "Whether prose describes the shipped behaviour without over- or under-claiming is a review judgement; the tests pin the constants and the OpenAPI paths, not the meaning of the delta paragraph."
  - id: D4
    description: "The archive route's OpenAPI entry declares application/zip, matching the FileResponse the route returns"
    requirement: EXP-02
    verification:
      - kind: integration
        ref: "tests/integration/api/test_openapi.py#test_openapi_exposes_the_public_contract (application/zip in the 200 content)"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-11-14
status: complete
---

# Phase 14 Plan 04: Public export contract, delta semantics and Produced Works Summary

**The partner document now carries the full ODbL export contract — two read-only endpoints, the seven frozen entries and their columns, the per-file origin ids, the MVCC delta chain (snapshot + watermark + from_seq/to_seq, `--since` as catch-up), the free-text CSV guard allow-list and present-sources attribution — and the OpenAPI schema declares the archive as `application/zip`.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 1
- **Files modified:** 4 (0 created)
- **Commits:** 1 measured (`git rev-list --count 64d2b27..HEAD`)

## Accomplishments

- **The contract is in `docs/public-api.md`, not inferred from code.** A new `## ODbL export` section documents the two routes, their cache headers, the one-404 rule (never 503), the anonymous quota, the seven ZIP entries, each CSV's header and the meaning of `label`/`value`/`handicap_families` as JSON.
- **Origin ids are stated per file**, as frozen in 14-02: places use `(source, origin_id)`, answers use `(place_id, criterion_slug)` and have no source-side surrogate, categories and criteria use `slug`. The `*_id` columns are labelled internal, so a partner does not key on them by mistake.
- **The delta contract is written as MVCC, not as a count.** `latest.json` carries `snapshot {name, seq}`, `watermark` and `retention_floor_seq` as separate fields; a delta contains exactly `watermark < seq <= safe_seq()` read in the same `REPEATABLE READ` transaction that streams the rows; each entry carries `from_seq`/`to_seq` so contiguity is verifiable; windows are applied in order and a delta is never described as cumulative. `--since` is documented as the cumulative catch-up and is refused below the retention floor.
- **The CSV guard is the shipped allow-list, not the plan's shorthand.** Places guard `name`, `address_full`, `city`, `source_category`; categories guard `name` and `label`; criteria guard `label`. Everything numeric, id, date or JSON is untouched, so a negative longitude and a `+` phone survive. `label` is JSON and cannot begin with a formula character, so listing it changes nothing in practice.
- **Attribution states the D-05 rule**: `ATTRIBUTION.txt` lists only sources present in that ZIP, with the legal name, last-update date and the reviewed `attribution_text` sentence from `licences.csv`; no per-row column, no hard-coded OSM or Overture line.
- **Produced Works and the forward-looking sentence are one string in two places.** Both were copied verbatim from `application/places/attribution.py`, and the new test imports those constants and asserts they appear in the Markdown.
- **OpenAPI parity fixed at the source.** The archive operation previously advertised `application/json`; the route now declares `response_class=FileResponse` and a `200` `application/zip` content, and the schema is regenerated.

## Task Commits

1. **Task 1: Document the export + Produced Works, regenerate OpenAPI** — `07580f3` (docs)

**Plan metadata:** the summary commit follows this file.

## Files Created/Modified

- `docs/public-api.md` — the `## ODbL export` section (endpoints, entries, columns, origin ids, delta contract, CSV guard, attribution, Produced Works), plus two narrow corrections: the header no longer calls `docs/openapi.json` "this file", and the final licence paragraph now points at `ATTRIBUTION.txt`.
- `docs/openapi.json` — regenerated; the only diff is the archive route's `200` content becoming `application/zip`.
- `tests/integration/api/test_openapi.py` — two export path assertions, the `application/zip` assertion, and the shared-constant docs assertion.
- `src/letmegetin/api/v1/export.py` — archive route declares `FileResponse` and its `200` media type.

## Verification (real output)

| Command | Result |
|---|---|
| `uv run python scripts/export_openapi.py` | exit 0, no output |
| OpenAPI byte stability: generate to a copy, regenerate, `cmp` | `OPENAPI BYTE-STABLE`, sha256 `f49d7a1b…` |
| `uv run pytest tests/integration/api/test_openapi.py -m integration -x` | **3 passed** in 0.37 s |
| `uv run pytest -q` | **481 passed**, 1 third-party `httpx` warning in 135 s (was 480 before this plan) |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `165 files already formatted` |
| `uv run mypy` | `Success: no issues found in 87 source files` |
| `node .gitnexus/run.cjs impact get_export_zip --direction upstream` | `risk: UNKNOWN`, 0 resolved callers — expected: FastAPI reaches it through the decorator, and the functional export suite exercises it. Search confirmed no direct Python caller before changing the decorator. |

The full suite was run on the commit before the last assertion was added; that assertion (the `application/zip` check) then passed in the focused openapi run above. No other code changed between the two runs.

## Decisions Made

- **Document the code's allow-list, not the plan's prose.** The plan said "categories/criteria name" and that `label` is never guarded; `FREE_TEXT_COLUMNS` guards categories `name`+`label` and criteria `label`. Since `label` is a JSON object it cannot trigger the guard, so the observable behaviour matches the plan, and the doc records the actual set.
- **Fix the media type in the route, regenerate the schema.** Hand-editing `docs/openapi.json` is forbidden; `response_class=FileResponse` plus an explicit `200` content is the smallest source-side fix, and it makes the machine contract match `application/zip`.
- **Two narrow doc corrections.** `this file: docs/openapi.json` was wrong in a document called `public-api.md`; the closing licence paragraph implied OSM and Overture ship in the export, which D-05 forbids. Both are inside the file this task owns.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] OpenAPI declared JSON for a ZIP archive**
- **Found during:** Task 1 (OpenAPI regeneration review)
- **Issue:** `GET /api/v1/export/{name}.zip` returned `application/zip` at runtime but its generated schema advertised `application/json` with an empty object, so a code-generated client would decode the archive wrongly.
- **Fix:** added `response_class=FileResponse` and a `200` response with `content: {application/zip: {}}` to the route decorator; regenerated `docs/openapi.json` with `scripts/export_openapi.py`; added an assertion on the media type.
- **Files modified:** `src/letmegetin/api/v1/export.py`, `docs/openapi.json`, `tests/integration/api/test_openapi.py`
- **Verification:** focused test 3 passed; full suite 481 passed; schema renders only `application/zip` for the 200.
- **Committed in:** `07580f3`

### Plan adjustments (documented, not defects)

**2.** `docs/openapi.json` already carried both export paths from 14-03. Regenerating it was byte-identical until the media-type fix; the file's diff is that fix, not the paths.
**3.** The CSV-guard section records the shipped `FREE_TEXT_COLUMNS` rather than the plan's shorthand (see Decisions).
**4.** The two narrow doc corrections (header sentence, final licence paragraph) are inside `docs/public-api.md` and serve the plan's own "do not over-claim" prohibition.

---

**Total deviations:** 1 auto-fixed (Rule 2) + 3 documented plan adjustments.
**Impact on plan:** no requirement lost; the only source change is the response declaration for an existing route.

## Threat Flags

None new. T-14-10 (information disclosure in the partner doc) stays `accept`: the documented surface is public by design, and every licence name and sentence is quoted from `licences.csv` or the shared constants — nothing was invented. T-14-11 did not fire: no package was added.

## Known Stubs

None. The doc documents the shipped files; the test imports the shipped constants.

## Issues Encountered

- The OpenAPI schema does not document the `404` responses as responses; the route descriptions state them in prose. Adding machine-readable `404`s would be a route change beyond this plan's contract, so it was left for a later pass.
- `git commit` reported "Unstaged files detected" and pre-commit stashed `.planning/STATE.md` / `.planning/state.json` (already dirty before this plan) and restored them; neither was staged or committed.

## Next Phase Readiness

- **14-05 (wrapper/timer):** the public contract is now in `docs/public-api.md`; extend `docs/deploy.md` with the timer and the Actions trigger, and do not add a competing export section there. The generation command must use the writable second mount from 14-03: `-v export_data:/data/export-rw api letmegetin-admin export odbl --out /data/export-rw`; the `:ro` target cannot be relaxed by `compose run -v`.
- The delta contract documents `latest.json` as the source of truth; 14-05's timer must not write `latest.json` by hand — only `export odbl` does.
- The archive route now advertises `application/zip`; any smoke test should assert that media type, not JSON.

---

## Self-Check: PASSED
