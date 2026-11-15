# Phase 16: OpenStreetMap — Pattern Map

**Mapped:** 2026-11-15
**Files classified:** 14 (create + modify)
**Analogs found:** 13 / 14 (the PBF reader has no analog — see "No Analog Found")

## How to read this

Every analog path below is git-tracked source under `src/`, `tests/` or `data/referential/`
(no `.gsd/capabilities/` mirror). "Copy from X lines a–b" means: replicate the *shape*, not
the AccesLibre-specific fields. The AccesLibre importer is deliberately the single template
for the OSM importer (the CONTEXT `existing_code_insights` says so): mirror it, don't invent a
second pipeline.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `src/letmegetin/application/places/import_osm.py` | service (use case) | streaming ingest | `application/places/import_acceslibre.py` | exact |
| `src/letmegetin/domain/places/osm_map.py` | utility (pure mapping) | transform | `domain/places/acceslibre_map.py` | exact |
| `src/letmegetin/application/places/osm_publish.py` | service (use case) | file-I/O (emit artefact) | `application/places/export.py` + `lov2_export.py` | exact |
| `src/letmegetin/domain/places/osm_change.py` (serialiser) | utility (pure) | transform | `domain/places/export_plan.py` | exact |
| `src/letmegetin/application/referential/osm_tags.py` (loader) | service (read-only loader) | file-I/O | `application/referential/families.py` | exact |
| `src/letmegetin/admin.py` | controller (CLI) | request-response | itself — `import_app`/`export_app` commands | exact |
| `data/referential/category_mapping.csv` | config (reviewed data) | — | itself (existing 158 rows) | modify |
| `data/referential/osm_accessibility_tags.csv` | config (reviewed data) | — | `data/referential/families.csv` | new |
| `data/referential/source_licences.csv` | config (reviewed data) | — | itself (add `osm;odbl;…`) | modify |
| `data/referential/` policy artefacts (wiki text, import plan, changeset comment, bot notes) | config (text) | — | `.planning/phases/15-…/15-PARTNER-ASK.md` | new |
| `tests/functional/places/test_osm_import.py` | test | — | `tests/functional/places/test_places_import.py` | exact |
| `tests/functional/places/test_osm_publish.py` | test | — | `tests/functional/places/test_lov2_export.py` | exact |
| `tests/unit/domain/places/test_osm_map.py` | test | — | `tests/unit/domain/places/test_acceslibre_map.py` | exact |
| `pyproject.toml` | config | — | itself (add `pyosmium`) | new dep |

---

## Pattern Assignments

### `src/letmegetin/application/places/import_osm.py` (service, streaming ingest)

**Analog:** `src/letmegetin/application/places/import_acceslibre.py` (354 lines, read whole file)

Copy the exact skeleton:

- **Row dataclass + report** (lines 55–86): `AcceslibreRow` → an `OsmRow` (fields: `source_id="node/123"`, `name`, `lat`, `lng`, `category_id`, `accessibility`, plus `osm_tags` for the unmatched-combination report). `ImportReport` (lines 77–86) already carries `created/linked/review/skipped/resolved/unresolved` — the OSM report adds `unmatched: dict[tuple[str, ...], int]` for D-06.
- **`SOURCE_ACCESLIBRE = "acceslibre"`** (line 33) → `SOURCE_OSM = "osm"` (D-03).
- **Streaming reader** (lines 179–208): `iter_acceslibre_rows` is a generator that opens a file handle and yields per row — the PBF reader is the same contract, a generator over a `pyosmium` handler (never materialised). Keep the `load_acceslibre_file` → `list(...)` materialisation seam (lines 206–208) for tests.
- **Category resolution memoised** (lines 247–256, 339–354): `resolve_category` result cached per label in a local dict. For OSM, the key is the `osm_tag` string; `resolve_category` is replaced by a lookup into `category_mapping.osm_tag` (see loader below). Keep the "skip and count" branch (lines 252–254) as D-06's skip-and-count.
- **Idempotent upsert** (lines 258–268): `get_by_source_id(SOURCE, source_id)` → if exists, `update` + `_write_source_data`, `report.skipped += 1`, return. The OSM importer reuses `get_by_source_id("osm", "node/123")` unchanged.
- **Dedup call site** (lines 270–271, 290–312): `_candidate` → `classify_match(score)` → `canonical_id`/`duplicate_of_id`/`merges.add`/`place_aliases.add`. Copy verbatim; this is the Phase-3 scorer and must stay source-agnostic.
- **Dry-run** (lines 302–303): `if dry_run: return` after counting, before `places.add`. Copy.
- **`ImportReport` returned to CLI** (lines 314–354).

The only new thing in the importer is the `pyosmium` handler that yields `OsmRow` — everything downstream is copy.

### `src/letmegetin/domain/places/osm_map.py` (utility, pure transform)

**Analog:** `src/letmegetin/domain/places/acceslibre_map.py` (49 lines)

- **`FIELD_MAP`/`accessibility_values`** (lines 13–48): the OSM twin is `OSM_TAG_MAP` mapping OSM tag keys (`wheelchair`, `ramp`, `toilets:wheelchair`…) → criterion slugs, and an `accessibility_values(tags)` that yields `{criterion_slug: {"value": …, "source": "osm", "key": tag}}`.
- **Critical difference — mapping is data, not code (D-05):** AccesLibre hard-codes `FIELD_MAP`; OSM must *not*. The tag→criterion map is read from `data/referential/osm_accessibility_tags.csv` (see loader below). `osm_map.py` holds only the pure `accessibility_values(tags, mapping)` transform + the `SOURCE = "osm"` constant. Do **not** hard-code `wheelchair` etc. — the CONTEXT D-05 rule is explicit.

### `src/letmegetin/application/referential/osm_tags.py` (loader, reviewed CSV)

**Analog 1:** `src/letmegetin/application/referential/families.py` lines 38–52 (`load_families`) — reviewed CSV → `dict`, fail-closed on duplicate slug, `|`-separated values, `DomainError` on unknown.

**Analog 2:** `src/letmegetin/application/places/lov2_export.py` lines 70–122 (`_read_csv`, `load_acceslibre_mapping`) — the stricter "reviewed file, exact header, duplicate is a gap" pattern. This is the right template for `osm_accessibility_tags.csv`: `_read_csv(path, ("osm_tag", "criterion_slug", …))`, raise `DomainError` on duplicate/empty row (fail-closed, never skip a mapping silently).

Copy the `_read_csv` shape (lines 70–79) verbatim; the OSM accessibility loader validates every `criterion_slug` against the criterion repository (like `apply_families` lines 69–73 unknown-slug check).

### `src/letmegetin/admin.py` (CLI registration)

**Analog:** itself. Copy:

- **Sub-app registration** (lines 113–139): add `osm_app = typer.Typer(...)` + `app.add_typer(osm_app, name="osm")`, or reuse `import_app` with an `osm` subcommand (lines 658–710 are the `import acceslibre` command to mirror: `--file`, `--dry-run`, `--no-dedup`, progress printer `_progress` lines 680–686, `_run_admin(callback, bump=False, commit=not dry_run)`).
- **`import_acceslibre_command`** (lines 658–710) is the exact template for `import osm --file france-latest.osm.pbf`. It already prints `created/linked/review/skipped/resolved/unresolved` and the top-20 unresolved (lines 701–708) — extend with the top unmatched tag combinations.
- **`export_odbl_command`** (lines 912–978) is the template for `osm publish --out …`: the fail-closed destination check (lines 933–937) and the report-print shape (lines 955–976). The publish command's gate is the reviewed ToS-consent flag + policy-artefact presence, mirroring `refuse_partner_window` (export.py lines 336–344).
- **`map_category` / `category_map`** (admin.py lines 227–255, `referential/admin.py` lines 231–251) already take an `--osm` option — the `osm_tag` review path exists; the importer reads the reviewed `osm_tag` from `category_mapping`, and this command is how an operator fills the remaining 124 rows.

### `data/referential/category_mapping.csv` + `source_licences.csv` (reviewed data)

**Loader:** `src/letmegetin/seed.py` lines 106–137 (`_load_category_mapping`) — upserts `osm_tag` by category slug into `CategoryMappingModel` (the `osm_tag` column already exists: `models.py` line 506, `repositories.py` lines 1406/1415). Filling the 124 empty `osm_tag` cells is a **data edit only** — no code.

**Licence:** `source_licences.csv` (3 lines today) gains `osm;odbl;<ISO date>`. `load_source_licences` (`licences.py` lines 114–138) already parses it; `licences.csv` already has the `odbl` row (line 3), and `licence_destinations.csv` already refuses `odbl;lov2_partner` (line 7) — LIC-03/D-12 needs **no code**, just the CSV row + a test that `odbl` cannot reach `lov2_partner` (already proven by `test_lov2_export.py` lines 216–233).

### `src/letmegetin/application/places/osm_publish.py` + `domain/places/osm_change.py` (writer)

**Analog 1 (writer):** `src/letmegetin/application/places/export.py`:
- `_write_atomic` (lines 148–156) — temp file + fsync + `os.replace`, so a reader never sees a half-written `.osmChange`.
- `_export_lock` (lines 159–168) — `flock` so one generator at a time.
- The fail-closed `licence_rules_count() == 0` guard (lines 379–383) is the shape of D-10's "refuse to write without policy artefacts".

**Analog 2 (gate + sidecar):** `src/letmegetin/application/places/lov2_export.py`:
- `build_lov2_feed` (lines 262–285) — reads reviewed data from `settings.data_dir`, decorates the repository, refuses when a gate is unmet (the `blocked` rule diverts everything: `test_lov2_export.py` lines 351–373). The OSM publish gate reads the ToS-consent flag + the four policy artefacts and **fails closed** if any is absent.
- `_write_mapping` (lines 249–259) — the `.osmChange` writer's atomic temp+replace shape.

**Analog 3 (pure serialiser):** `src/letmegetin/domain/places/export_plan.py`:
- `CsvRow`/`SourcedRow` Protocols (lines 80–96) + `to_csv()` row dataclasses (lines 138–278) — the OSM twin is a pure `.osmChange` XML/`<node>`/`<way>` serialiser with no SQLAlchemy/FastAPI imports (module docstring lines 3–9).

### Tests

- **Importer:** `tests/functional/places/test_osm_import.py` copies `test_places_import.py` (241 lines): inline CSV/PBF fixture, `require_database("place")`, `_CLEANUP` by `source='osm'` prefix, `CliRunner().invoke(admin.app, ["import", "osm", "--file", …])`, assert `created=/linked=/skipped=` and idempotency (lines 68–91), dry-run writes nothing (lines 189–199), streaming-not-list guard (lines 228–241). Replace the CSV fixture with a tiny synthetic PBF (or a fake `pyosmium` handler) — the PBF is the only new fixture.
- **Publisher:** `tests/functional/places/test_osm_publish.py` copies `test_lov2_export.py` (441 lines): the `partner_data` fixture (lines 46–69) copies reviewed CSVs into a `tmp_path` and `monkeypatch.setattr(settings, "data_dir", data)` — this is exactly how the OSM tests pin the reviewed `osm_accessibility_tags.csv` and the ToS-consent flag. Copy the fail-closed tests (lines 427–441) and the "refuses delta / refuses served dir" tests (lines 329–348).
- **Mapping unit test:** `tests/unit/domain/places/test_osm_map.py` copies `tests/unit/domain/places/test_acceslibre_map.py` shape (FIELD_MAP bijectivity assert, `accessibility_values`).

---

## Shared Patterns

### Freshness / conflict guard (applies to the importer)
**Source:** `src/letmegetin/infrastructure/persistence/repositories.py` lines 392–411 (`_rejection`) + lines 1061–1176 (`upsert_accessibility`).
An import may only replace a row of its own source and only with a claim at least as fresh. The OSM importer does **not** reimplement this — it calls the same `upsert_accessibility` with `source="osm"`.

### Provenance stamping (applies to the importer)
**Source:** `repositories.py` `add` lines 860–892 — every place write resolves `source_license` via `_source_licence` (lines 842–858), which reads `source_licences.csv` and raises `DomainError` if `osm` has no reviewed row. The planner must add the `osm` row to `source_licences.csv` *before* the importer runs, or every OSM row fails with the message already written in that method.

### Reviewed-data-over-branches (D-05, D-10, D-12)
**Source:** `domain/places/licence.py` lines 1–30 — `can_redistribute`/`DESTINATIONS` is data-driven, fail-closed on missing. The OSM accessibility mapping and the publish gate follow the same rule: never branch on a tag value or a policy in importer/publisher code.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| PBF reader (inside `import_osm.py`) | streaming source | streaming | **No `pyosmium`, no `.pbf`, no Overpass reader exists anywhere in `src/` or `pyproject.toml`** (grep confirms: the only `osm` hits are the `CategoryMappingModel.osm_tag` column, `seed._load_category_mapping`, `map_category`, and docstrings). This is the first new dependency since the project began (D-01). The planner must specify the `pyosmium.SimpleHandler` streaming shape itself; the *contract* (a generator of `OsmRow`) is what the rest of the code mirrors from AccesLibre. |

---

## Risks the planner must carry

1. **`pyosmium` is a new dependency (D-01).** First package added since project start. Needs `pyproject.toml` + `uv lock`, and a decision on how the PBF reader is invoked (native C++ binding, separate process vs in-process). No existing pattern to copy; budget a spike.
2. **The Geofabrik extract is not vendored.** `france-latest.osm.pbf` is ~4 GB and downloaded at run time by the operator. Tests cannot use it — the planner must define a tiny synthetic PBF fixture (or a fake handler) or the functional import test is not runnable in CI.
3. **`osm_tag` covers only 34 of 158 categories.** D-04 imports *all mapped categories* — the import will skip and count the vast majority of POIs until an operator reviews the remaining 124 `osm_tag` rows. The "top unmatched tag combinations" report (D-06) is the growth mechanism, but the first import will be nearly empty of mapped POIs. Planner should sequence the CSV completion review as its own plan.
4. **`osm_accessibility_tags.csv` shape is unspecified.** D-05 lists candidate tags (`wheelchair`, `ramp`, `handrail`, `toilets:wheelchair`) but the mapping must land on our criteria slugs, several of which are option/boolean typed. The loader's fail-closed validation (unknown criterion = `DomainError`) will surface mismatches late; plan a review pass against the criteria tree before import.
5. **Publish gate is fail-closed on artefacts that don't exist yet (D-10).** The import plan, wiki text, changeset-comment template and bot-account notes must all be authored in-phase before the generator writes anything. If the planner defers one, the publisher is dead code. The `.osmChange` serialiser has no in-repo analog either (no XML emitter exists).

## Metadata

**Analog search scope:** `src/letmegetin/` (application/places, application/referential, domain/places, domain/referential, infrastructure/persistence), `data/referential/`, `tests/`, `pyproject.toml`.
**Files scanned:** 15 source files + 2 CSVs + grep for OSM/PBF/pyosmium/osmChange.
**Pattern extraction date:** 2026-11-15.
