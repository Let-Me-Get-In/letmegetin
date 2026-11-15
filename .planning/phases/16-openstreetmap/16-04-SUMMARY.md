---
phase: 16-openstreetmap
plan: 04
subsystem: places
tags: [osm, osmchange, publish, xml, cli, throttle, gate, postgis]

requires:
  - phase: 16-openstreetmap (16-01)
    provides: place.osm_version, place.osm_tags, import osm, source='osm' rows
  - phase: 16-openstreetmap (16-02)
    provides: reviewed osm_accessibility_tags.csv, source_licences osm;odbl
provides:
  - domain/places/osm_change.py — the pure osmChange 0.6 serialiser (modify/node, full tag set)
  - osm_publish use case — fail-closed gate, stored-tags ∪ mapped-tags element, atomic file write
  - OSM_THROTTLE_SECONDS = 5.0 — the constant the future uploader reads (D-10)
  - PlaceRepository.list_by_source — the source scan the publisher needs
  - `osm publish --out` CLI writing answers.osmChange, never uploading (D-09)
affects: [16-05 policy artefacts and upload plan]

actuals:
  tokens: 6361
  tasks: 3
  commits: 3

plan_head_before: 095f811a646baafc4fd4eb5eaf18514381c0a762
plan_head_after: e134dc1c32be54c92d66bcf7af3355697eedd353

tech-stack:
  added: []
  patterns:
    - "Non-destructive write-back: a <modify> carries the stored raw tag set merged with our answer; an absent stored set refuses and counts (BLOCKER 1)"
    - "Fail-closed artefact gate before any file exists: ToS flag + five policy files, checked before the first DB read"
    - "Atomic single-file artefact: temp + fsync + os.replace, the export.py shape without a ZIP"

key-files:
  created:
    - src/letmegetin/domain/places/osm_change.py
    - src/letmegetin/application/places/osm_publish.py
    - tests/unit/domain/places/test_osm_change.py
    - tests/functional/places/test_osm_publish.py
  modified:
    - src/letmegetin/admin.py
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/infrastructure/persistence/repositories.py

key-decisions:
  - "The serialiser takes the already-merged tag mapping and emits it verbatim: it cannot drop a tag the use case passed, so non-destructiveness is a structural property, not a convention"
  - "A place is refused when it has no reviewed inverse mapping, no stored osm_tags, no osm_version, no node/<digits> id, or no coordinates — each reason is counted and printed"
  - "Answers are inverted from the reviewed osm_accessibility_tags.csv at run time (data, never a branch, D-05); only answers with a reviewed inverse can be written back"
  - "Elements are sorted by numeric object id before serialising, so two runs over the same data produce the same document"
  - "The functional merge proof uses a user-contributed answer whose tag is absent from the stored set, so the element can only carry it if the merge adds it (stronger than seeding the tag twice)"
  - "No licence-matrix re-check in publish: every reviewed source is allowed to the osm destination and only source='osm' places are emitted; a shortcut: comment names the upgrade condition"

patterns-established:
  - "Publish gate: artefact presence + an explicit `accepted` flag, refused before any query (D-10/D-11)"
  - "Artefact generation is one atomic file in an operator-chosen --out, with no network module imported (D-09)"

requirements-completed: [OSM-02]

coverage:
  - id: D1
    description: "The pure serialiser emits one <modify> <node> with the action, numeric id, version, lat/lon and every tag, XML-escaped, no I/O"
    requirement: OSM-02
    verification:
      - kind: unit
        ref: "tests/unit/domain/places/test_osm_change.py (2 tests: shape + escaping)"
        status: pass
    human_judgment: false
  - id: D2
    description: "osm publish emits the stored osm_tags merged with the mapped accessibility answer; the stored tags survive and the answer's tag is added"
    requirement: OSM-02
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_publish.py::test_osm_publish_emits_the_stored_tags_merged_with_the_answer"
        status: pass
    human_judgment: false
  - id: D3
    description: "A place whose stored osm_tags is NULL, and a way, are not emitted and appear in the report with their reason"
    requirement: OSM-02
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_publish.py::test_osm_publish_emits_the_stored_tags_merged_with_the_answer"
        status: pass
    human_judgment: false
  - id: D4
    description: "OSM_THROTTLE_SECONDS is defined in osm_publish.py and is positive"
    requirement: OSM-02
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_publish.py::test_osm_throttle_is_a_positive_constant"
        status: pass
    human_judgment: false
  - id: D5
    description: "The gate fails closed: any missing policy artefact or a non-`accepted` ToS flag raises DomainError, exits 1 and writes no file"
    requirement: OSM-02
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_publish.py (8 parametrised cases: 5 missing artefacts, 3 consent variants)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The publish path imports no network client (D-09: file generated, never uploaded)"
    requirement: OSM-02
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_publish.py::test_osm_publish_module_imports_no_network_client"
        status: pass
    human_judgment: false
  - id: D7
    description: "import → publish round trip: node/1's emitted tag set equals the fixture's raw tags plus the mapped accessibility tag, version preserved"
    requirement: OSM-02
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_publish.py::test_import_then_publish_emits_the_raw_tags_plus_the_mapped_answer"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-11-16
status: complete
---

# Phase 16 Plan 04: OpenStreetMap publish tracer Summary

**One `source='osm'` place flows out as a single `.osmChange` `<modify>` element carrying its stored raw tags merged with our accessibility answer — refused and counted when the stored tag set is absent, and never written without the policy gate**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-11-16
- **Tasks:** 3
- **Files modified:** 7 (4 created, 3 modified)
- **Commits:** 3 (measured: `095f811..e134dc1`)

## Accomplishments

- **The serialiser is non-destructive by construction.** `serialize_element` receives the full,
  already-merged tag mapping and emits every pair; it has no way to drop a tag its caller passed.
  XML escaping covers keys and values, including `&`, `<` and `"`.
- **The publish use case merges the stored tag set with our answer, and refuses the rest.** Stored
  `osm_tags` ∪ the mapped accessibility tags is what lands in the element. A place with no stored
  set, no version, no `node/<digits>` id or no coordinates is not emitted and is counted with a
  stable reason that the CLI prints.
- **The gate is fail-closed.** `data_dir/osm/` must hold the five policy artefacts and a
  `tos_consent.txt` whose content (trailing newlines stripped) is exactly `accepted`; otherwise
  `DomainError` → exit 1 and no file. The check runs before the first query.
- **`OSM_THROTTLE_SECONDS = 5.0`** is a real constant with the D-10 rationale in a comment, pinned
  positive by a test and read by nothing in this phase.
- **No upload exists.** The module imports no `socket`, `httpx`, `requests`, `aiohttp`, `urllib`
  or `osmium`; the test parses its AST to say so. The only artefacts are `<out>/answers.osmChange`
  (atomic temp + fsync + `os.replace`) and the report lines.

## Task Commits

1. **Task 1: the pure .osmChange serialiser** — `a96967b` (feat)
2. **Task 2: osm_publish use case + gate + `osm publish` CLI** — `fc0df19` (feat)
3. **Task 3: functional publish proof** — `e134dc1` (test)

## Files Created/Modified

- `src/letmegetin/domain/places/osm_change.py` — `serialize_element` / `serialize_document`,
  `osmChange 0.6` root, modify/node with id, version, lat/lon and every tag
- `src/letmegetin/application/places/osm_publish.py` — `OSM_THROTTLE_SECONDS`, `POLICY_ARTEFACTS`,
  `OsmPublishReport`, `format_publish_report`, `osm_publish`, the gate and the atomic writer
- `src/letmegetin/admin.py` — `osm publish --out` under the existing `osm` sub-app
- `src/letmegetin/domain/places/repositories.py` — `PlaceRepository.list_by_source` port
- `src/letmegetin/infrastructure/persistence/repositories.py` — its SQL implementation
- `tests/unit/domain/places/test_osm_change.py` — element shape + escaping
- `tests/functional/places/test_osm_publish.py` — 12 tests: merge, refusal, throttle, gate
  (parametrised), no-network, import→publish round trip

## Decisions Made

- **The inverse of `osm_accessibility_tags.csv` is the definition of "allowed to leave".** Only an
  answer whose `(criterion_slug, criterion_value)` has a reviewed row can be expressed as an OSM
  tag; everything else is counted under `no reviewed accessibility answer to publish`. The licence
  matrix is not re-read: all reviewed sources are already allowed to the `osm` destination and only
  `source='osm'` places are scanned. A `shortcut:` comment in the module states the upgrade
  condition (re-check with `can_redistribute` when a source OSM may not receive is added).
- **The functional merge proof uses a user-contributed answer.** The direct-seed place stores
  `{amenity, name}` and the answer is a `user` value for `wheelchair=yes`, so the element can only
  contain it if the merge *adds* it — and it can only keep `amenity`/`name` if the merge does not
  replace the stored set. Seeding `wheelchair=yes` in both places would have proven nothing.
- **Elements sort by numeric object id.** Two runs over unchanged data yield byte-identical
  documents, which is what a reviewer diffs.
- **Direct SQL seeding in the functional test** (place + `place_accessibility` rows), so no import,
  no export-event journal and no licence snapshot stand between the fixture and the assertion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `PlaceRepository.list_by_source` did not exist**
- **Found during:** Task 2 (`osm_publish` needs to enumerate `source='osm'` places)
- **Issue:** the port could fetch one place by id/slug/source-id and count by source, but had no
  way to list a source's rows; `ExportPlanRepository.stream_*` returns `PlaceRow`, which carries
  neither `osm_version` nor `osm_tags`.
- **Fix:** added `list_by_source(source) -> list[Place]` to the port and the SQL adapter
  (`ORDER BY place.id`), returning full entities. GitNexus rates the port HIGH risk (15 importing
  modules) but the change is purely additive; mypy and the full suite confirm no implementation
  breaks.
- **Files modified:** `src/letmegetin/domain/places/repositories.py`,
  `src/letmegetin/infrastructure/persistence/repositories.py`
- **Verification:** full suite green (658 passed); the publish scan is exercised by 12 functional
  tests.
- **Committed in:** `fc0df19`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** None on scope. The plan named no data-access seam for the source scan; this is
the minimum one, reused by any future per-source generator.

## Issues Encountered

- The plan's `--out` in the Task 3 example was the same tmp directory as the fixture
  `data_dir`. The test uses `<tmp>/out` instead, so the gate's `data_dir/osm/` cannot be confused
  with the artefact directory; nothing else changes.
- `gitnexus detect-changes` reports risk "high" on the Task 2 commit because hunk attribution
  flags neighbouring symbols (`import_reclassify`, `get_by_slug`, `list_for_dedup`); the realised
  changes are the additive `list_by_source` and the new module. The index was reindexed to `095f811`
  before any `impact` answer was trusted.
- No alembic step: this plan adds no column and no table.

## Verification

| Command | Result |
|---|---|
| `uv run pytest tests/unit/domain/places/test_osm_change.py -m unit -x` | `2 passed` (RED first: `ModuleNotFoundError`) |
| `…/letmegetin_test uv run pytest tests/functional/places/test_osm_publish.py -m functional -x` | `12 passed` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `200 files already formatted` |
| `uv run mypy` | `Success: no issues found in 100 source files` |
| `…/letmegetin_test uv run pytest -q` (whole suite) | `658 passed` in 194s |

## Known Stubs

None. The gate intentionally depends on files 16-05 will author; the functional test supplies
them, and the module's docstring states 16-05 owns their content.

## Threat Flags

None new. The publisher's only new surfaces are a local-directory read behind the D-10 gate and a
local file write; it imports no network client (asserted).

## Next Phase Readiness

- **16-05 authors these six files under `data/referential/osm/`** and the publisher starts writing
  without a code change: `import_plan.md`, `wiki_page.md`, `discussion_url.txt`,
  `changeset_comment_template.txt`, `bot_account.md`, `tos_consent.txt` (content `accepted`).
  `POLICY_ARTEFACTS` and `TOS_CONSENT` in `osm_publish.py` are the contract.
- **`OSM_THROTTLE_SECONDS` is the seam** the future uploader reads; nothing sleeps on it yet.
- **`format_publish_report` is complete**, so `osm publish` needs no change when 16-05 lands.
- **The scan is a full `list_by_source`.** A national `source='osm'` table (~600k rows) materialises
  as entities before the batched answer query; if 16-05 turns publish into a repeated operation,
  stream it the way `ExportPlanRepository` streams places. Not a blocker for the tracer.
- **Linked OSM rows are emitted**: the generator reads `source='osm'` rows directly and never
  filters on `canonical_id` (16-03's note).

---

*Phase: 16-openstreetmap*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk; all three task commits (`a96967b`, `fc0df19`, `e134dc1`) are
ancestors of HEAD.
