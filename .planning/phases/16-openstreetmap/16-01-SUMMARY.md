---
phase: 16-openstreetmap
plan: 01
subsystem: places
tags: [osm, osmium, pbf, importer, postgis, jsonb, alembic, cli]

requires:
  - phase: 12-place-write-path
    provides: PlaceRepository.add/update, export_event journal, source_licence resolution
  - phase: 03-dedup
    provides: the source-agnostic (source, source_id) unique index and merge machinery
provides:
  - osmium pinned (>=4.3.2,<5) behind a lazy, guarded infrastructure adapter
  - OsmRow contract (source_id, name, point, full raw tag set, object version)
  - iter_osm_rows: a streaming, pull-based PBF reader
  - place.osm_version + place.osm_tags (migration 0016) and their entity/model/repository mapping
  - CategoryMappingRepository.resolve_osm_tag (the reviewed OSM tag → category seam)
  - import_osm use case + `import osm --file` CLI writing idempotent source='osm' place rows
affects: [16-02 accessibility mapping, 16-03 dedup wiring, 16-04 .osmChange generator]

actuals:
  tokens: 20740
  tasks: 2
  commits: 2

tech-stack:
  added: ["osmium>=4.3.2,<5 (pyosmium distribution: the Python binding of libosmium)"]
  patterns:
    - "Pull-based generator over osmium.FileProcessor (no SimpleHandler callback, no materialisation)"
    - "Lazy guarded third-party import so one optional binding never breaks the rest of the CLI"

key-files:
  created:
    - src/letmegetin/domain/places/osm_map.py
    - src/letmegetin/infrastructure/osm_pbf.py
    - src/letmegetin/application/places/import_osm.py
    - migrations/versions/0016_osm_identity.py
    - tests/fixtures/osm_pbf.py
    - tests/functional/places/test_osm_import.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/letmegetin/domain/places/entities.py
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/infrastructure/persistence/models.py
    - src/letmegetin/infrastructure/persistence/mappers.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/admin.py

key-decisions:
  - "osmium.FileProcessor(...).with_locations() iterated directly: the plan's `locations=True` constructor argument does not exist in osmium 4.3.2"
  - "osm_version + osm_tags are plain place columns, never part of the export_event payload (the prohibition)"
  - "A re-run refreshes osm_version/osm_tags in place when the object version changed, and writes nothing otherwise (D-02)"
  - "Untagged objects are geometry, not POIs: dropped before resolution; unmapped tagged objects are skipped and counted"
  - "The functional test seeds the osm;odbl source_licence row itself, because the reviewed CSV row is 16-02's change"

patterns-established:
  - "PBF reader: one generator, one OsmRow at a time, no list() over the processor (D-01)"
  - "Reviewed-data-over-branches: category resolution reads category_mapping.osm_tag, never a tag literal (D-05)"
  - "Skip-and-count: an unmatched tag combination is reported for CSV growth, never guessed into a category (D-06)"

requirements-completed: [OSM-01]

coverage:
  - id: D1
    description: "A synthetic .osm.pbf streams through iter_osm_rows into OsmRow objects carrying source_id, tags and version; a missing osmium raises a domain error instead of skipping silently"
    requirement: OSM-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_import.py#test_osm_import_writes_one_place_with_version_and_raw_tags"
        status: pass
    human_judgment: false
  - id: D2
    description: "`import osm --file` writes one idempotent source='osm' place row (source_id node/1, mapped cafe category, osm_version, full raw osm_tags); a re-run changes nothing; unmapped node/2 and way/100 stay absent and are counted"
    requirement: OSM-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_import.py (4 tests: write, idempotency, dry-run, skip-and-count)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-16
status: complete
---

# Phase 16 Plan 01: OpenStreetMap import tracer Summary

**A synthetic PBF streams through osmium into one `source='osm'` place row carrying the OSM object version and its full raw tag set, idempotent on re-run**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-11-15T22:52:00Z
- **Completed:** 2026-11-15T22:59:49Z
- **Tasks:** 2 (Task 1 was the package checkpoint, resolved before execution)
- **Files modified:** 14 (6 created, 8 modified)

## Accomplishments

- `osmium>=4.3.2,<5` pinned and locked — the first new runtime dependency since the project began — behind
  the only module that imports it, lazily and with a loud `DomainError` when absent.
- `iter_osm_rows` streams a `.osm.pbf` as a pull generator: nodes become `node/<id>`, ways become
  `way/<id>` at their first resolvable node, relations are out of scope. Nothing materialises the file.
- `place.osm_version` (Integer) and `place.osm_tags` (JSONB) migrated, mapped through entity/model/
  mapper/repository — the two facts the `.osmChange` `<modify>` needs to be non-destructive.
- `resolve_osm_tag` resolves only reviewed `category_mapping.osm_tag` values; an unmapped POI is
  skipped and counted with its tag combination (D-06), never guessed into a category.
- `import osm --file <pbf>` (with `--dry-run` and `--no-dedup`) writes idempotent place rows through the
  Phase-12 write path, proven end to end by four functional tests on a generated PBF.

## Task Commits

1. **Task 2: pin osmium, the OsmRow contract, and the lazy streaming PBF reader** — `572b1a7` (feat)
2. **Task 3: osm_version + osm_tags columns, import_osm use case, and import osm CLI** — `d2c6856` (feat)

## Files Created/Modified

- `pyproject.toml`, `uv.lock` — `osmium>=4.3.2,<5` in `[project].dependencies`, locked by `uv lock`
- `src/letmegetin/domain/places/osm_map.py` — `SOURCE = "osm"` and the frozen `OsmRow`
- `src/letmegetin/infrastructure/osm_pbf.py` — streaming reader, lazy guarded `osmium` import
- `src/letmegetin/application/places/import_osm.py` — `OsmImportReport`, `resolve_osm_category`,
  `render_unmatched`, `_import_row`, `import_osm`
- `migrations/versions/0016_osm_identity.py` — adds/drops `osm_version` and `osm_tags`
- `src/letmegetin/domain/places/entities.py` — `Place.osm_version`, `Place.osm_tags`
- `src/letmegetin/domain/places/repositories.py` — `CategoryMappingRepository.resolve_osm_tag`
- `src/letmegetin/infrastructure/persistence/models.py` — the two columns on `PlaceModel`
- `src/letmegetin/infrastructure/persistence/mappers.py` — map both fields
- `src/letmegetin/infrastructure/persistence/repositories.py` — write both in `add`/`update` (fill-only on
  update, like `erp_slug`), implement `resolve_osm_tag`; `_PLACE_PAYLOAD_COLUMNS` untouched
- `src/letmegetin/admin.py` — `import osm` command with the stderr progress printer
- `tests/fixtures/osm_pbf.py` — three-object synthetic PBF via `osmium.SimpleWriter`
- `tests/functional/places/test_osm_import.py` — 4 tests: write, idempotency, dry-run, skip-and-count

## Decisions Made

- **`with_locations()` instead of the plan's `locations=True`.** `osmium.FileProcessor` takes no such
  constructor argument in 4.3.2; `FileProcessor(path).with_locations()` is the documented equivalent and
  is what enriches way node lists with coordinates.
- **`isinstance(obj, osmium.osm.Node/Way)` instead of `obj.is_node()`.** The wheel ships real type stubs
  but `is_node()` is not a `TypeGuard`, so the union never narrows and mypy reports 16 `union-attr`
  errors. `isinstance` narrows correctly and keeps the global mypy config untouched.
- **Name and tag guards, in that order.** Untagged objects are a way's geometry (dropped before any
  lookup); a tagged object with no reviewed match is skipped **and counted** (D-06); a mapped object
  with no name is dropped because `place.name` is required and a nameless place is not searchable.
- **Re-run semantics.** `existing.osm_version != row.version` refreshes the OSM identity (category,
  `source_category`, version, tags, `retrieved_at`); an unchanged re-run writes nothing and counts
  `skipped`. The name is never rewritten from a re-import (the AccesLibre precedent).
- **The unmatched report keeps the full tag set**, including `name=…`, exactly as the plan specifies.
  Filtering a tag key out would be a hard-coded OSM tag in importer code (the prohibition).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The osmium wheel ships `py.typed` and real stubs, so the instructed `# type: ignore[import-untyped]` was not added**
- **Found during:** Task 2 (PBF reader)
- **Issue:** The execution brief asked for a targeted `# type: ignore[import-untyped]` on the lazy
  import to cover a mypy gap. `osmium` 4.3.2 ships `py.typed` plus `.pyi` files, so there is no gap:
  mypy is clean with and without the directive. An unused ignore would assert something false about the
  package.
- **Fix:** No ignore. The real gap was elsewhere: the stubs are precise enough that `obj.is_node()`
  does not narrow the `Node | Way | Relation | Area | Changeset` union, producing 16 `union-attr`
  errors. Narrowed with `isinstance(obj, osmium.osm.Node/Way)` inside `iter_osm_rows` — local, no
  global mypy weakening.
- **Files modified:** `src/letmegetin/infrastructure/osm_pbf.py`
- **Verification:** `uv run mypy` → "Success: no issues found in 97 source files".
- **Committed in:** `572b1a7`

**2. [Rule 3 - Blocking] The OSM place write needs a `source_licence` row that only 16-02 adds**
- **Found during:** Task 3 (functional test)
- **Issue:** `SqlAlchemyPlaceRepository.add` snapshots the source licence and raises `DomainError` when
  the source has no reviewed row. `data/referential/source_licences.csv` has no `osm` line, and adding
  it here would duplicate the append 16-02 owns (a duplicate CSV row is a fail-closed error in that
  loader).
- **Fix:** The functional test seeds `licence('odbl')` + `source_licence('osm','odbl')` in an
  `osm_licence` fixture and removes only the row it created. The reviewed CSV row stays 16-02's change.
- **Files modified:** `tests/functional/places/test_osm_import.py`
- **Verification:** the four functional tests pass; `test_osm_import_writes_one_place_with_version_and_raw_tags`
  asserts `source_license = 'odbl'` on the created row.
- **Committed in:** `d2c6856`

**3. [Rule 1 - Bug] Unnamed/untagged objects were counted as unmatched tag combinations**
- **Found during:** Task 3 (first functional run: `unresolved=1` instead of `2`)
- **Issue:** The first draft returned on a missing name *before* resolving the category, so `way/100`
  (no name) never reached the skip-and-count path, and the way's untagged geometry nodes would have
  been counted as an empty tag combination.
- **Fix:** Resolve first, then: no tags → return (geometry), no match → count and skip, mapped but
  nameless → return, otherwise resolved.
- **Files modified:** `src/letmegetin/application/places/import_osm.py`
- **Verification:** `unresolved=2` with `unmatched: highway=residential=1` and
  `name=Antiquités shop=antiques=1`.
- **Committed in:** `d2c6856`

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug)
**Impact on plan:** None on scope. The two blocking items were environment facts (real type stubs; the
licence row belongs to the next plan); the bug was a guard-ordering defect the functional test caught
on its first run.

## Issues Encountered

- The plan's Task 3 `<verify>` runs `uv run alembic upgrade head` unqualified. That would migrate the
  **dev** database, which the execution rules forbid. Every alembic/pytest invocation was run with
  `LETMEGETIN_DATABASE_URL=postgresql+asyncpg://letmegetin:letmegetin@localhost:55433/letmegetin_test`.
  Migration 0016 applied cleanly to the test database.
- `osmium` writes PBF objects in the order they are added: the fixture adds nodes 1, 2, 10, 11 before
  way 100, which the reader needs for way geometry.

## Verification

| Command | Result |
|---|---|
| `LETMEGETIN_DATABASE_URL=…/letmegetin_test uv run alembic upgrade head` | `Running upgrade 0015 -> 0016, OSM object identity on place` |
| `LETMEGETIN_DATABASE_URL=…/letmegetin_test uv run pytest tests/functional/places/test_osm_import.py -m functional -x` | `4 passed` |
| `uv run ruff check src/letmegetin` | `All checks passed!` |
| `uv run ruff format --check .` | `191 files already formatted` |
| `uv run mypy` | `Success: no issues found in 97 source files` |
| `uv run pytest -q` (whole suite, regression sweep) | `597 passed` in 163s |

## Known Stubs

None that block the plan. Three deliberate inert seams, each owned by the next plan and stated in the
`import_osm` module docstring: `_write_source_data` (accessibility values, 16-02), the `dedup` argument
(candidate lookup + merge log, 16-03), and `render_unmatched`'s ranking (16-03 may reorder it; the
report is already populated and printed).

## Threat Flags

None — the only new surface is an operator-supplied local file read by `import osm --file`, which is
the boundary already registered as T-16-01.

## Next Phase Readiness

- 16-02 can wire accessibility values: `import_osm` already takes `categories`, `criteria` and the
  reviewed tag seam (`resolve_osm_tag`), and `place.osm_tags` holds the raw set the mapping reads.
- 16-03 can wire dedup: `place_aliases`, `merges` and `dedup` are already in the signature, and the
  unmatched counter is populated for the report it completes.
- 16-04/16-05 can emit `.osmChange`: every OSM row now carries its object version and full raw tag set.
- Blocker for the real import: `category_mapping.osm_tag` covers 34 of 158 categories and
  `source_licences.csv` has no `osm` row — both are 16-02's deliverables.

---
*Phase: 16-openstreetmap*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk; both task commits (`572b1a7`, `d2c6856`) are ancestors of HEAD.
