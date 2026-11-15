---
phase: 16-openstreetmap
plan: 02
subsystem: places
tags: [osm, reviewed-data, accessibility, licence, audit, cli, postgis]

requires:
  - phase: 16-openstreetmap (16-01)
    provides: OsmRow, iter_osm_rows, import osm, CategoryMappingRepository.resolve_osm_tag, place.osm_version/osm_tags
  - phase: 12-place-write-path
    provides: upsert_accessibility freshness guard, _source_licence resolution, export_event journal
provides:
  - category_mapping.csv reviewed to 124/158 osm_tag cells, each fill marked `osm_tag review: 2026-11-16`
  - source_licences.csv `osm;odbl`, so a source='osm' write resolves ODbL with no hand seeding
  - osm_accessibility_tags.csv (4 reviewed rows) + its fail-closed loader and accessibility_gaps audit
  - osm_map.accessibility_values (pure transform over the reviewed mapping)
  - `import osm` writing the mapped accessibility value through upsert_accessibility
  - `osm tags audit` CLI (exit 1 on any category/criterion gap) and CategoryMappingRepository.list_osm_tags
affects: [16-03 dedup wiring, 16-04 .osmChange generator, 17-overture]

actuals:
  tokens: 12286
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Reviewed-data-over-branches, second instance: the accessibility mapping is a CSV read at run time, never a tag literal in the importer (D-05)"
    - "Fail-closed on authored data, forgiving on unmapped tags: a malformed/illegal reviewed row raises before the first POI; a tag pair the review omitted is simply dropped (D-06)"
    - "Audit as a gate: a completeness command prints each gap and exits 1, so a mapping mistake is a red build, not a silent mis-import"

key-files:
  created:
    - data/referential/osm_accessibility_tags.csv
    - src/letmegetin/application/referential/osm_tags.py
    - tests/unit/application/referential/test_osm_tags.py
    - tests/unit/domain/places/test_osm_map.py
    - tests/functional/places/test_osm_licence.py
  modified:
    - data/referential/category_mapping.csv
    - data/referential/source_licences.csv
    - src/letmegetin/domain/places/osm_map.py
    - src/letmegetin/domain/places/repositories.py
    - src/letmegetin/infrastructure/persistence/repositories.py
    - src/letmegetin/application/places/import_osm.py
    - src/letmegetin/admin.py
    - tests/fixtures/osm_pbf.py
    - tests/functional/places/test_osm_import.py

key-decisions:
  - "90 categories gain a reviewed osm_tag (124/158 mapped); 34 stay empty because OSM has no distinct node/way tag for them (denominations vs place_of_worship, school levels vs amenity=school, lodging subtrees, generic buckets)"
  - "wheelchair=yes/limited map onto the two options of circulation-acces-en-fauteuil-a-tout-le-lieu, not the plan's illustrative entree-acces: that criterion is entrance-level and an option criterion needs an option slug, so the invented value would have been a guess"
  - "wheelchair=no, ramp, handrail and hearing_loop are deliberately NOT mapped: no criterion they can legally answer (ramp/handrail are geometry keys on steps, virtually never on a POI)"
  - "A reviewed row that names an unknown criterion or an illegal typed value raises before the first POI (fail closed); a tag pair the review omitted is dropped at run time (D-06) — the two rules are distinct"
  - "The OSM licence is one CSV row, zero code: the existing odbl->lov2_partner denial (LIC-03) is what refuses it"

patterns-established:
  - "accessibility_gaps(criteria, mapping) is the single typed-value predicate; the importer raises on it and the audit prints it"
  - "``osm`` typer sub-app holds the OSM commands (audit now, publish in 16-04)"

requirements-completed: [OSM-01]

coverage:
  - id: D1
    description: "category_mapping.csv osm_tag is reviewed for every category with a genuine OSM equivalent (124/158); the 34 empty cells are reviewed decisions, and each fill carries `osm_tag review: 2026-11-16`"
    requirement: OSM-01
    verification:
      - kind: other
        ref: "python -c CSV shape check (single key=value, no whitespace) — 0 invalid rows"
        status: pass
    human_judgment: true
    rationale: "Whether a French place category has a genuine OSM equivalent is a taxonomy judgement no assertion can prove; the diff is the artefact to review."
  - id: D2
    description: "source_licences.csv carries osm;odbl; an imported source='osm' place resolves source_license='odbl', odbl may reach the osm destination and never lov2_partner"
    requirement: OSM-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_licence.py (2 tests: imported row carries odbl, matrix refusal from the reviewed CSVs)"
        status: pass
    human_judgment: false
  - id: D3
    description: "osm_accessibility_tags.csv maps the reviewed accessibility set onto typed criteria; the loader fails closed on a wrong header, empty field, duplicate pair or extra column"
    verification:
      - kind: unit
        ref: "tests/unit/application/referential/test_osm_tags.py (15 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "accessibility_values turns a matching raw tag pair into the criterion's typed value and drops everything unreviewed"
    verification:
      - kind: unit
        ref: "tests/unit/domain/places/test_osm_map.py (7 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "`import osm` writes the mapped accessibility value for wheelchair=yes, still imports a mapped POI with no accessibility tags, refuses an incoherent mapping before writing anything, and `osm audit` exits 1 on a gap"
    requirement: OSM-01
    verification:
      - kind: integration
        ref: "tests/functional/places/test_osm_import.py (10 tests)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-11-16
status: complete
---

# Phase 16 Plan 02: OpenStreetMap reviewed data and accessibility Summary

**Reviewed OSM category tags at 124/158, four defended accessibility mappings written through the import, and the OSM ODbL licence row — all as data, gated by an `osm audit` that exits 1 on any gap**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-11-15T23:04:16Z
- **Completed:** 2026-11-15T23:18:00Z
- **Tasks:** 3
- **Files modified:** 14 (5 created, 9 modified)

## Accomplishments

- **The category bridge is reviewed, not filled.** 90 empty `osm_tag` cells gained a single canonical
  `key=value` verified against the OSM wiki (taginfo usage counts + wiki status for the less common
  ones: `shop=houseware`, `shop=leather`, `office=diplomatic`, `amenity=training`…). 34 stay empty
  by decision: denominations are `amenity=place_of_worship` (already held by `place_of_worship`),
  school levels all share `amenity=school`, `gite`/`vacation_appartment`/`lodging`/`luxury_hotel`
  have no distinct tag, and `national_park` is a `boundary` relation the node/way reader never sees.
  Every fill carries `osm_tag review: 2026-11-16` in `notes`, so the review is visible in the diff.
- **The OSM licence is one CSV row.** `osm;odbl;2026-11-15` makes an OSM write resolve its licence;
  the existing `odbl;lov2_partner;false` row is what refuses it to a partner destination. No branch
  was added and `test_lov2_export.py` still passes unchanged.
- **The accessibility mapping is four rows, each defended.** `wheelchair=yes|limited` map onto the
  two options of `circulation-acces-en-fauteuil-a-tout-le-lieu`; `toilets:wheelchair=yes|no` onto
  the two `services-et-equipements-sanitaires` options. `wheelchair=no`, `ramp`, `handrail` and
  `hearing_loop` are deliberately absent — no criterion they can legally answer.
- **Import writes it.** `import osm` loads and validates the mapping once, then writes the mapped
  value through the Phase-12 `upsert_accessibility` (journal, freshness, licence snapshot), and a
  mapped POI with no accessibility tag still imports as an empty place to fill (D-04).
- **The gate exists.** `osm audit` prints every gap — an unknown criterion slug, a value illegal for
  the criterion's type, an `osm_tag` naming no category — and exits 1.

## Task Commits

1. **Task 1: review the category osm tags and map osm to odbl** — `c3103c0` (feat)
2. **Task 2: load the reviewed accessibility mapping and audit it** — `0d5b4e0` (feat)
3. **Task 3: import accessibility values, audit the tags** — `b0b0450` (feat)
4. **Fixture fix: keep the unmapped fixture POI unmapped after the tag review** — `36eb4fc` (test)

**Plan metadata:** see the docs commit that carries this file.

## Files Created/Modified

- `data/referential/category_mapping.csv` — 90 reviewed `osm_tag` fills + their `notes` marker
- `data/referential/source_licences.csv` — the `osm;odbl;2026-11-15` row
- `data/referential/osm_accessibility_tags.csv` — the reviewed accessibility set (4 rows, typed values)
- `src/letmegetin/application/referential/osm_tags.py` — `load_osm_accessibility_tags`,
  `accessibility_gaps`, `audit_osm_tags`
- `src/letmegetin/domain/places/osm_map.py` — `AccessibilityMapping` + `accessibility_values`
- `src/letmegetin/application/places/import_osm.py` — mapping load + validation, `_write_source_data`
- `src/letmegetin/admin.py` — `osm` sub-app and `osm audit`
- `src/letmegetin/domain/places/repositories.py`, `.../infrastructure/persistence/repositories.py` —
  `list_osm_tags()` (`osm_tag -> category slug`) on the mapping repository and its port
- `tests/unit/domain/places/test_osm_map.py`, `tests/unit/application/referential/test_osm_tags.py`
- `tests/functional/places/test_osm_licence.py`, `tests/functional/places/test_osm_import.py`
- `tests/fixtures/osm_pbf.py` — `with_bakery` flag (a mapped POI with no accessibility tag)

## Decisions Made

- **The plan's illustrative `wheelchair=yes -> entree-acces` was not implemented.** `entree-acces` is
  an *option* criterion about the entrance; its legal values are its own child slugs. `wheelchair`
  is a venue-level claim, and the venue-level criterion that expresses exactly OSM's
  `yes`/`limited` pair is `circulation-acces-en-fauteuil-a-tout-le-lieu`
  (`…-acces-en-fauteuil-possible-partout` / `…-certains-espaces-ne-sont-pas-accessibles-en-fauteuil`).
  Writing the plan's example literally would have meant inventing a value type.
- **`ramp` and `handrail` are not mapped.** They are keys on steps/highway segments (Key:ramp,
  Key:handrail), virtually never on the POI itself; mapping them would guess an entrance claim from
  a geometry tag. Same for `hearing_loop`: the referential has no criterion for it.
- **No boolean criterion exists in the seeded referential** (every base criterion is an option with
  children, plus one integer and one string). The boolean rule (`true`/`false`) is therefore
  implemented and unit-tested with a fake criterion, and currently unreachable from real data.
- **Fixture tag change.** `shop=antiques` became a reviewed category in this plan, so the "unmapped"
  fixture node had to move to a tag no category claims (`amenity=drinking_water`).
- **`osm audit` follows the `families audit` shape, not `_run_admin`.** `_run_admin` echoes one
  message and cannot print a gap list before exiting 1; the audit precedent in the same file already
  does what this command needs (see deviation 3).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `list_osm_tags()` added to the repository port and its SQL adapter**
- **Found during:** Task 3 (`osm audit`)
- **Issue:** The plan said "add a small `list_osm_tags()` if none exists"; it did not exist, and
  `resolve_osm_tag(tag)` cannot enumerate the reviewed tags.
- **Fix:** `list_osm_tags() -> dict[str, str]` (osm_tag → category slug, joined on `categories`)
  on `SqlAlchemyCategoryMappingRepository` and the `CategoryMappingRepository` port.
- **Files modified:** `src/letmegetin/domain/places/repositories.py`,
  `src/letmegetin/infrastructure/persistence/repositories.py`
- **Verification:** `osm audit` prints "osm tags ok" against the seeded referential; `uv run mypy`
  clean.
- **Committed in:** `b0b0450`

**2. [Rule 2 - Missing Critical] The PBF fixture gained a `with_bakery` flag**
- **Found during:** Task 3 (the D-04 test)
- **Issue:** "a mapped POI with no accessibility tags still imports" needs a second mapped object.
  Adding it unconditionally would have changed the fixture's documented three-object contract that
  16-04's `<modify>` test relies on, and would have broken 16-01's counts.
- **Fix:** `write_osm_pbf(path, *, with_bakery=False)`; the default fixture is unchanged.
- **Files modified:** `tests/fixtures/osm_pbf.py`
- **Verification:** the 16-01 tests keep their counts; the new test asserts `created=2` and no
  `place_accessibility` row for `node/3`.
- **Committed in:** `b0b0450`

**3. [Rule 2 - Missing Critical] `osm audit` uses the audit command shape, not `_run_admin`**
- **Found during:** Task 3 (`osm audit`)
- **Issue:** the plan asked for `_run_admin(callback, bump=False)`, which echoes a single return
  string. The audit must print every gap (one per line) and then exit 1; converting that into a
  single message would hide exactly the information the gate exists to give (WARNING 3/T-16-03).
- **Fix:** the `families_audit` shape (an async reader + `asyncio.run`), plus the `DomainError ->
  typer.Exit(1)` mapping a malformed CSV needs. Both paths exit 1 and print.
- **Files modified:** `src/letmegetin/admin.py`
- **Verification:** `test_osm_audit_exits_one_on_an_incoherent_mapping` asserts exit 1 and the named
  criterion; `test_osm_audit_passes_on_the_reviewed_data` asserts 0.
- **Committed in:** `b0b0450`

**4. [Rule 1 - Bug] The "unmapped" fixture node resolved once the reviewed CSV was seeded**
- **Found during:** the plan-level verification run, after the full suite had seeded the test
  database from the reviewed CSVs
- **Issue:** `node/2` was `shop=antiques`; this plan maps `shop=antiques` to
  `antique_furniture_store`, so it started resolving (`created=2`, `unresolved=1`) and the
  skip-and-count assertion failed. CI seeds before running the suite (`.github/workflows/ci.yml`
  line 150), so this would have failed there too.
- **Fix:** `node/2` is now `amenity=drinking_water` ("Fontaine du Coin"), a real OSM tag no reviewed
  category claims.
- **Files modified:** `tests/fixtures/osm_pbf.py`, `tests/functional/places/test_osm_import.py`
- **Verification:** the full suite (627 tests) and the OSM functional files pass after a fresh
  `python -m letmegetin.seed` against the test database.
- **Committed in:** `36eb4fc`

**5. [Rule 2 - Missing Critical] The `osm_licence` fixture in `test_osm_import.py` was simplified**
- **Found during:** Task 3
- **Issue:** 16-01's fixture hand-inserted `licence('odbl')` and `source_licence('osm','odbl')`
  because the reviewed CSV row did not exist yet. With the row in place that hand-seeding hides a
  regression: if `source_licences.csv` lost the osm row, the fixture would keep the test green.
- **Fix:** the fixture is now `seed_source_licences()`, which reads the reviewed CSV — the row's
  existence is what the test proves.
- **Files modified:** `tests/functional/places/test_osm_import.py`
- **Verification:** 10 functional OSM import tests pass; `test_osm_licence.py` fails loudly if the
  row is removed.
- **Committed in:** `b0b0450`

---

**Total deviations:** 5 auto-fixed (4 missing critical, 1 bug)
**Impact on plan:** No scope creep. Four of the five are seams the plan itself pointed at
(`list_osm_tags`, "add the missing `_write_source_data`", the fixture); the fifth is a defect this
plan's own review introduced and the full suite caught.

## Issues Encountered

- The plan's Task 3 `<verify>` runs `uv run alembic upgrade head` unqualified, which would migrate
  the **dev** database. Every alembic and pytest invocation was run with
  `LETMEGETIN_DATABASE_URL=postgresql+asyncpg://letmegetin:letmegetin@localhost:55433/letmegetin_test`;
  alembic reported no pending migration (0016 already applied).
- `GitNexus detect-changes` reports "Risk level: high" for the Task 3 commit because its hunk→symbol
  attribution flags neighbouring symbols (`LabelPairs`, `import_report`, `duplicates_list`, `upsert`)
  that this plan did not edit. The edited symbols are additive (`osm_audit`, `list_osm_tags`,
  `_write_source_data`) or parameter additions, and the full suite is green (627 passed).
- The test database was seeded from the reviewed CSVs mid-verification, which is what exposed
  deviation 4. A `python -m letmegetin.seed` re-run afterwards reports `mapping=158`,
  `124` mapped `osm_tag` cells and the `osm -> odbl` source licence.

## Verification

| Command | Result |
|---|---|
| `uv run pytest tests/unit/domain/places/test_osm_map.py -m unit -x` | `7 passed` |
| `uv run pytest tests/unit/application/referential/test_osm_tags.py -m unit -x` | `15 passed` |
| `…/letmegetin_test uv run pytest tests/functional/places/test_osm_import.py -m functional -x` | `10 passed` |
| `…/letmegetin_test uv run pytest tests/functional/places/test_osm_licence.py -m functional -x` | `2 passed` |
| `python -c` CSV shape check (`key=value`, no whitespace) | `invalid osm_tag rows: []` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `195 files already formatted` |
| `uv run mypy` | `Success: no issues found in 98 source files` |
| `…/letmegetin_test uv run pytest -q` (whole suite, regression sweep) | `627 passed` in 183s |
| `…/letmegetin_test uv run python -m letmegetin.seed` | `mapping=158`, `124/158` mapped, `osm -> odbl` present |

## Known Stubs

None. `import_osm`'s `dedup` argument and the candidate lookup remain inert by design; 16-03 owns
them and the module docstring says so.

## Threat Flags

None new. The reviewed CSVs are the already-registered boundary (T-16-03 / T-16-04), and both are
now gated by `osm audit` and by the loader's fail-closed checks.

## Next Phase Readiness

- **16-03 (dedup) can wire the candidate lookup.** `import_osm` still accepts `dedup`, `categories`,
  `place_aliases` and `merges` and does nothing with them; `_write_source_data` shows the shape the
  per-row write uses.
- **16-04 (`osm publish`) has its sub-app.** Extend `osm_app` in `admin.py`; the fixture's documented
  three-object contract is intact (`with_bakery` is opt-in), so `node/1` is still the single
  `<modify>` candidate with its version and full tag set.
- **The operator's first real import works without hand seeding**: `osm -> odbl` exists and
  `category_mapping` covers 124/158 categories. `letmegetin-admin licences sync` (or a seed) loads
  the new row into an existing database.
- **34 categories remain unmapped by decision.** Growing them starts from the `unmatched` report
  (`import osm` prints the top 20 tag combinations), not from a target count.

---
*Phase: 16-openstreetmap*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk; all four task commits (`c3103c0`, `0d5b4e0`, `b0b0450`, `36eb4fc`)
are ancestors of HEAD.
