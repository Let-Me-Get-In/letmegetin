---
phase: 15-acceslibre-round-trip
verified: 2026-11-15T20:46:27Z
status: human_needed
score: 24/25 must-haves verified
covered_files: [".planning/phases/15-acceslibre-round-trip/15-01-PLAN.md", ".planning/phases/15-acceslibre-round-trip/15-01-SUMMARY.md", ".planning/phases/15-acceslibre-round-trip/15-02-PLAN.md", ".planning/phases/15-acceslibre-round-trip/15-02-SUMMARY.md", ".planning/phases/15-acceslibre-round-trip/15-03-PLAN.md", ".planning/phases/15-acceslibre-round-trip/15-03-SUMMARY.md", ".planning/phases/15-acceslibre-round-trip/15-04-PLAN.md", ".planning/phases/15-acceslibre-round-trip/15-04-SUMMARY.md", ".planning/phases/15-acceslibre-round-trip/15-05-PLAN.md", ".planning/phases/15-acceslibre-round-trip/15-05-SUMMARY.md", ".planning/phases/15-acceslibre-round-trip/15-06-PLAN.md", ".planning/phases/15-acceslibre-round-trip/15-06-SUMMARY.md", "data/referential/acceslibre_identifier_rule.csv", "data/referential/acceslibre_mapping.csv", "data/referential/licence_destinations.csv", "data/referential/licences.csv", "data/referential/source_licences.csv", "docs/public-api.md", "migrations/versions/0014_place_erp_slug.py", "migrations/versions/0015_acceslibre_push_write.py", "pyproject.toml", "src/letmegetin/admin.py", "src/letmegetin/application/places/export.py", "src/letmegetin/application/places/import_acceslibre.py", "src/letmegetin/application/places/lov2_export.py", "src/letmegetin/application/places/push_acceslibre.py", "src/letmegetin/config.py", "src/letmegetin/domain/places/acceslibre_map.py", "src/letmegetin/domain/places/acceslibre_push.py", "src/letmegetin/domain/places/entities.py", "src/letmegetin/domain/places/export_plan.py", "src/letmegetin/domain/places/lov2_projection.py", "src/letmegetin/infrastructure/acceslibre/__init__.py", "src/letmegetin/infrastructure/acceslibre/client.py", "src/letmegetin/infrastructure/persistence/export_repositories.py", "src/letmegetin/infrastructure/persistence/mappers.py", "src/letmegetin/infrastructure/persistence/models.py", "src/letmegetin/infrastructure/persistence/push_repositories.py", "src/letmegetin/infrastructure/persistence/repositories.py", "tests/functional/places/test_acceslibre_push.py", "tests/functional/places/test_lov2_export.py", "tests/functional/places/test_provenance_write.py", "tests/functional/referential/test_admin_cli.py", "tests/functional/test_licence_migration.py", "tests/integration/acceslibre/__init__.py", "tests/integration/acceslibre/fakes.py", "tests/integration/acceslibre/test_client.py", "tests/integration/acceslibre/test_probe.py", "tests/integration/referential/test_seed_vocabulary.py", "tests/unit/domain/places/test_acceslibre_push.py", "tests/unit/domain/places/test_lov2_projection.py", "tests/unit/infrastructure/acceslibre/test_client_security.py", "uv.lock"]
covered_digest: "v4:sha256:3042c5e841fb63a961ea1c5cf6cf4e3de509ff728fa8df1b3e9a8c14ffb5bb6a"
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "`acceslibre probe <source_id>` resolves the identifier rule and confirms A2 (the live read `accessibilite` section) against AccesLibre"
    test: "Provide LETMEGETIN_ACCESLIBRE_API_KEY (LET-130) and run `scripts/with-secrets.sh uv run python -m letmegetin.admin acceslibre probe <origin_id>`."
    expected: "Both `list_erps` lookups return the ERP (or none), GET /api/erps/<slug>/ prints the real `accessibilite` keys, and `data/referential/acceslibre_identifier_rule.csv` records `origin_id`/`slug`/`blocked` plus its detail."
    why_human: "The five stub-backed tests prove the code path only. No key exists, so the live response shape (A2) and Open Question 1 (is our origin_id the ERP slug?) are still assumptions; the committed rule stays `blocked;UNVERIFIED`."
human_verification:
  - test: "Live read-only probe: `scripts/with-secrets.sh uv run python -m letmegetin.admin acceslibre probe <origin_id>` with LETMEGETIN_ACCESLIBRE_API_KEY"
    expected: "Two list_erps lookups and one get_erp succeed and print the `accessibilite` section keys (A2); the rule CSV moves off `blocked` to the identifier that actually addresses the ERP. Until then places.csv stays header-only and every place diverts to mapping.csv."
    why_human: "Requires the AccesLibre partner key requested in 15-PARTNER-ASK.md; a stub cannot establish the live read contract. Owner ticket: LET-130."
  - test: "No-op PATCH on staging: `acceslibre push --dry-run` on one known place, then one PATCH of that ERP's current value"
    expected: "HTTP 200 with an `ErpImport` body and the written value under the real `accessibilite` key names (A1). Any 4xx/5xx or different key name is a contract change the push must absorb before a production run."
    why_human: "15-05 Task 3 is a blocking-human checkpoint; the functional tests substitute an in-process fake (`FakeAccesLibre`), so A1 and the write key name are unverified against the live service. Owner ticket: LET-130."
---

# Phase 15: AccesLibre round trip Verification Report

**Phase Goal:** Owned rows flow back to AccesLibre as a lov2 feed, and our answers push to their API idempotently.
**Verified:** 2026-11-15T20:46:27Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `export_odbl`/`_write_zip` take a `destination`; no `DESTINATION` constant remains | ✓ VERIFIED | `src/letmegetin/application/places/export.py:239,355,406`; `grep DESTINATION` returns nothing; `admin.py:921-953` threads `--destination`. |
| 2 | Partner archive lands in the operator `--out`, never the served dir; public routes untouched | ✓ VERIFIED | `admin.py:931-937` refuses `--out == settings.export_dir`; `tests/functional/places/test_lov2_export.py:186-213` asserts the ZIP is under `out`, the served dir is untouched, `GET /api/v1/export/<partner>.zip` is 404 and the public `latest.json` is unchanged; `:339-348` asserts the guard exits 1. |
| 3 | Only matrix-allowed rows reach the feed; `odbl`/`cdla` absent and counted | ✓ VERIFIED | `export_repositories.py:64-78` (`_licence_allows`, fail-closed on NULL); `test_lov2_export.py:216-233` asserts `lov2` present, `odbl`/`cdla` absent, and manifest `excluded_places` counts both. |
| 4 | `httpx` is a runtime dependency; no new package | ✓ VERIFIED | `pyproject.toml:20` under `[project] dependencies`; absent from the dev group; `uv lock --check` green. |
| 5 | Adapter: fixed origin, `Api-Key`, TLS on, no redirects, key never leaked | ✓ VERIFIED | `infrastructure/acceslibre/client.py:17,41-50,72-83`; `tests/unit/infrastructure/acceslibre/test_client_security.py` asserts constant origin, `verify=True`, `follow_redirects=False`, error text has status+slug and not the key; `tests/integration/acceslibre/test_client.py:34-145`. |
| 6 | Pure typed diff + amended-D-11 freshness (`observed_at` else `recorded_at` vs their `updated_at`) | ✓ VERIFIED | `domain/places/acceslibre_push.py:103-152`; `tests/unit/domain/places/test_acceslibre_push.py:58-107` (string-vs-bool ignored, NULL `observed_at` still wins, newer remote skips). |
| 7 | Outbound value validated; unknown rejected, never coerced to null | ✓ VERIFIED | `acceslibre_push.py:110-114,169-200`; unit tests `:110-132` reject out-of-range int, unknown enum, `None`, `user_id`; the functional `test_an_out_of_type_value_is_journaled_not_coerced` journals `invalid_value` and never GETs/PATCHes. |
| 8 | `resolve_identifier(rule, erp_slug, origin_id)` is the single key rule; `blocked` → None | ✓ VERIFIED | `acceslibre_push.py:86-100`; unit tests `:33-44`; consumed by the projection (`lov2_projection.py:283`) and push (`push_acceslibre.py:109`). |
| 9 | Application use cases depend on domain ports only (no SQLAlchemy/httpx) | ✓ VERIFIED | `push_acceslibre.py:15-29` imports only domain modules + `DomainError`; the adapter is the sole httpx importer; `mypy` clean. |
| 10 | Nullable `place.erp_slug` via migration 0014 | ✓ VERIFIED | `migrations/versions/0014_place_erp_slug.py`; `models.py:234`; dev DB at `0015 (head)`; `test_reimport...` reads/writes it. |
| 11 | Identifier-rule CSV holds one rule; default `blocked;UNVERIFIED`; probe writes it | ✓ VERIFIED | `data/referential/acceslibre_identifier_rule.csv`; `lov2_export.py:81-91` fails closed unless exactly one rule; `admin.py:1143-1194`; `tests/integration/acceslibre/test_probe.py` (three outcomes + refusal writes nothing). |
| 12 | `acceslibre probe` reads `list_erps` + `get_erp` and prints A2 | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Code path verified (`admin.py:1151-1219`; 5 stub tests). The live read contract (A2) and Open Question 1 are NOT established: no key exists, the committed rule is `blocked;UNVERIFIED`. See Human Verification #1. |
| 13 | Feed entries carry partner keys (identifier/activite/8 field names), never `slug`/`category_slug`/`criterion_slug` | ✓ VERIFIED | `lov2_projection.py:30-79`; `test_cli_emits_partner_keys_in_every_entry` (`test_lov2_export.py:236-281`) asserts all five headers, `identifier=="feed-1"`, `activite`, the 8 field names, `field=="entree_pmr"`, alias pair. |
| 14 | Unmappable place/category/criterion never enters the feed; each lands in the mapping document with a reason | ✓ VERIFIED | `lov2_export.py:137-245` diverts to `mapping.csv`; `test_mapping_document_names_every_unmappable_place` (`:284-311`) and `test_blocked_rule_diverts_every_place` (`:351-364`). Caveat: the diverted category rows are labelled `entity=place` (see W-2). |
| 15 | Mapping document covers every DB criterion outside the 8 mapped columns; test fails on a gap | ✓ VERIFIED | `data/referential/acceslibre_mapping.csv` (232 criterion rows, none of the 8 mapped); `test_every_db_criterion_is_in_the_mapping_document` (`:314-326`) asserts DB minus FIELD_MAP ⊆ document. |
| 16 | `erp_slug` is filled by re-import when the rule is `slug`; owned answers survive the re-import | ✓ VERIFIED | `test_reimport_preserves_owned_answers_and_fills_the_erp_slug` (`:379-409`): `erp_slug` None → `lieu-reprise-123`, user answer still `("user","false")`. |
| 17 | New append-only `acceslibre_push_write` table with decision/reason CHECKs, keeping the losing value | ✓ VERIFIED | `migrations/versions/0015_acceslibre_push_write.py`; `models.py:355-385`; `test_the_journal_keeps_our_value_on_every_decision` asserts two `skipped/their_fresher` rows keeping `True` and `90`. |
| 18 | Owned-row stream: `source='user'` + licence gate + `yield_per`, never materialised | ✓ VERIFIED | `push_repositories.py:31-107` (window ranking, `_licence_allows(..., destination)`, `yield_per=_PAGE`); `test_a_withheld_licence_is_never_pushed` asserts zero GET, zero PATCH, zero journal. |
| 19 | Read-then-diff: one GET per place, PATCH only differing fields, journal every decision, replay is a no-op | ✓ VERIFIED (against an in-process fake; live A1 unverified — Human Verification #2) | `push_acceslibre.py:101-161`; `test_dry_run_prints_the_diff_and_writes_nothing`, `test_a_replayed_push_patches_nothing` (second run: no new PATCH, no new accepted row). |
| 20 | `acceslibre push [--dry-run]` is the only write path; dry run writes nothing; missing key exits 1 | ✓ VERIFIED | `admin.py:1242-1266`; `test_dry_run...` asserts no PATCH/journal; `test_a_missing_key_is_a_domain_error` exit 1; live CLI: push exit 1 with `no AccesLibre API key`. |
| 21 | `dual` licence + attribution_text naming both; `user→dual`; `dual→lov2_partner/open_export/osm` | ✓ VERIFIED | `data/referential/licences.csv`, `licence_destinations.csv`, `source_licences.csv`; `licences audit` exits 0. |
| 22 | `licences sync`/`audit` pass with the dual rows | ✓ VERIFIED | `licences audit` → "licences ok: every licence has a full matrix and every row resolves"; `test_licence_migration.py` syncs. |
| 23 | A new user answer is stamped `dual` and appears in `answers.csv` of a lov2 snapshot; odbl/cdla absent; ATTRIBUTION names both | ✓ VERIFIED | `test_new_user_answer_is_dual_and_reaches_the_lov2_feed` (`test_licence_migration.py:146-170`): stamped `dual`, `field=entree_pmr`, `source_license=dual`, odbl/cdla absent, dual name in ATTRIBUTION. |
| 24 | A later import cannot overwrite a fresher community contribution | ✓ VERIFIED | `repositories.py:392-411` (`_rejection`: a user row is never replaced by another source; same-source freshness rejects an older/NULL claim); `test_an_import_cannot_overwrite_a_user_row` and the freshness matrix in `tests/functional/places/test_provenance_conflict.py:124-170`. |
| 25 | `new-only` honoured: no 0016 migration, no code re-stamps `source_license` retroactively | ✓ VERIFIED | No `0016_*` file; `grep` finds no re-stamp path (only migration 0011's reviewed-source backfill); `user;dual;2026-11-15` is applied at write time by `_source_licence`. |

**Score:** 24/25 truths verified (1 present, behavior-unverified: live probe/A2)

### Decision-Gated Item (not counted)

| Item | Resolution | Evidence |
|------|------------|----------|
| 15-06 Task 3: re-stamp EXISTING `odbl` user rows to `dual` (migration 0016) | ⊘ NOT REQUIRED — operator chose `new-only` on 2026-11-15 | `15-06-SUMMARY.md:96-120`; `15-SECURITY.md:43,56,72-91`; no `migrations/versions/0016_*`; no re-stamping code. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/letmegetin/infrastructure/acceslibre/client.py` | fixed-origin adapter | ✓ VERIFIED | 106 lines, sole httpx importer, bounded retry, redacted errors. |
| `src/letmegetin/domain/places/acceslibre_push.py` | pure decision + ports + resolver | ✓ VERIFIED | 207 lines, no I/O imports. |
| `src/letmegetin/domain/places/lov2_projection.py` | pure partner projection | ✓ VERIFIED | 381 lines; 27 unit tests. |
| `src/letmegetin/application/places/lov2_export.py` | decorator + feed + mapping sidecar | ✓ VERIFIED | 284 lines; 10 functional tests. |
| `src/letmegetin/application/places/push_acceslibre.py` | read-then-diff use case | ✓ VERIFIED | 228 lines; 9 functional tests. |
| `src/letmegetin/infrastructure/persistence/push_repositories.py` | stream + journal adapter | ✓ VERIFIED | 134 lines; licence gate inside the stream. |
| `migrations/versions/0014_place_erp_slug.py` | `place.erp_slug` | ✓ VERIFIED | applies from 0013; dev DB at head 0015. |
| `migrations/versions/0015_acceslibre_push_write.py` | journal table | ✓ VERIFIED | two CHECKs + `place_id` index. |
| `data/referential/acceslibre_mapping.csv` | reviewed mapping document | ✓ VERIFIED | 366 rows: 232 criteria, 133 categories, 1 D-05 note. |
| `data/referential/acceslibre_identifier_rule.csv` | single recorded rule | ✓ VERIFIED | `blocked;UNVERIFIED` (designed fail-closed). |
| `docs/public-api.md` | partner-facing contract | ✓ VERIFIED | §"lov2 partner feed" at :323-352; `dual` added to `source_license` at :219. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `admin export odbl --destination lov2_partner` | `build_lov2_feed` | local import, `admin.py:940-944` | ✓ WIRED | CLI dispatches to the feed builder. |
| `build_lov2_feed` | `export_odbl` + `Lov2ExportRepository` + `LOV2_HEADERS` | `lov2_export.py:261-283` | ✓ WIRED | Writer sees only projected rows. |
| `Lov2ExportRepository` | `resolve_identifier` / `canonical_activites` / `THEIR_FIELD_FOR_SLUG` | `lov2_projection.py:283,321,338,358` | ✓ WIRED | Every key resolves through the single rule. |
| `identifier_rule.csv` | feed and push | `load_identifier_rule` in `lov2_export.py:81` and `admin.py:1256` | ✓ WIRED | Same loader, same file. |
| `push_acceslibre` | `AccesLibrePort` + `AccesLibrePushRepositoryPort` | `push_acceslibre.py:47-58` | ✓ WIRED | CLI supplies `SqlAlchemyPushRepository` + `AccesLibreClient`. |
| `stream_owned_answers(destination)` | `_licence_allows(source_license, destination)` | `push_repositories.py:64` | ✓ WIRED | Destination is a bound parameter. |
| `licences.csv` `dual` | `_source_licence('user')` → `place_accessibility.source_license` | `repositories.py:1081`; `test_licence_migration.py:154-157` | ✓ WIRED | New write is stamped `dual`. |
| `dual → lov2_partner` | feed/push licence gate | `export_repositories.py:64-78` | ✓ WIRED | Data-only widening. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `places.csv` (partner) | `identifier` | `PlaceModel.erp_slug`/`source_id` via `resolve_identifier` | Yes (real DB rows; 0 today only because the rule is blocked) | ✓ FLOWING |
| `answers.csv` (partner) | `field`, `value` | `place_accessibility` joining `criteria`, licence-gated | Yes (1,702,243 real rows measured) | ✓ FLOWING |
| `mapping.csv` | diverted entity/reason | `Lov2ExportRepository.unmappable` + reviewed CSV | Yes (393 rows measured) | ✓ FLOWING |
| `acceslibre_push_write` | decision/value | `stream_owned_answers` → diff → journal | Yes (real DB; 0 rows today because there are 0 user answers) | ✓ FLOWING |
| ATTRIBUTION | licence names | `_licence_catalogue()` + `_Presence` | Yes (lists `acceslibre` today; `dual` only when a dual row is exported) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `uv run pytest -q` | 593 passed, 1 warning, 156.06s | ✓ PASS |
| Phase functional | `uv run pytest tests/functional/places/test_lov2_export.py tests/functional/places/test_acceslibre_push.py tests/functional/test_licence_migration.py -q` | 20 passed, 25.59s | ✓ PASS |
| Phase unit + integration | `uv run pytest tests/unit/domain/places/test_lov2_projection.py tests/unit/domain/places/test_acceslibre_push.py tests/unit/infrastructure/acceslibre/ tests/integration/acceslibre/ -q` | 84 passed, 0.41s | ✓ PASS |
| Lint | `uv run ruff check .` | All checks passed | ✓ PASS |
| Format | `uv run ruff format --check .` | 185 files already formatted | ✓ PASS |
| Types | `uv run mypy` | Success: no issues found in 94 source files | ✓ PASS |
| Security scan | `uv run bandit -r src -c pyproject.toml` | High 0, Medium 0, Low 0 | ✓ PASS |
| Licence audit | `uv run python -m letmegetin.admin licences audit` | "licences ok: every licence has a full matrix and every row resolves" | ✓ PASS |
| Probe fail-closed | `env -u LETMEGETIN_ACCESLIBRE_API_KEY … acceslibre probe 12345` | exit 1, "never calls AccesLibre unauthenticated" | ✓ PASS |
| Push fail-closed | `env -u LETMEGETIN_ACCESLIBRE_API_KEY … acceslibre push --dry-run` | exit 1, "no AccesLibre API key" | ✓ PASS |
| Real partner export (dev DB, committed `blocked` rule) | `… export odbl --destination lov2_partner --out <tmp>` | ZIP + latest.json + mapping.csv written; places.csv=0, categories=133, criteria=8, answers=1,702,243, aliases=0; mapping.csv=392 data rows | ✓ PASS (see residual observations) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` exists and no PLAN/SUMMARY declares one. The plan's "probe" is the
`acceslibre probe` CLI command, whose stub tests run as part of the suite; its live run is the human
item above. Step 7c: NOT APPLICABLE.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PART-01 | 15-01, 15-03, 15-04, 15-06 | lov2 feed of owned rows keyed on their identifiers, categories/criteria in their vocabulary, plus a mapping document listing every unmatchable place and why | ✓ SATISFIED (mechanically; production keying still `blocked` by design) | Destination threading, licence gate, projection, mapping sidecar and `dual` licence all verified; the operator's `blocked` rule leaves `places.csv` header-only until LET-130. |
| PART-02 | 15-02, 15-03, 15-05, 15-06 | Operator pushes our answers idempotently, with conflict rules/provenance strong enough that a later import cannot overwrite a fresher community contribution | ⚠️ PARTIALLY VERIFIED — live write contract (A1) unverified | Adapter, typed diff, amended-D-11 freshness, journal, CLI and the import-conflict path are verified; the first real PATCH and the real `accessibilite` key names are the open human item (LET-130). |

No orphaned requirements: `REQUIREMENTS.md` maps only PART-01/PART-02 to Phase 15, and both appear in plans.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/letmegetin/application/places/lov2_export.py` | 221 | A category with no inverse is diverted through `UnmappablePlace`, so the mapping sidecar labels it `entity=place` with a category slug as identifier (measured: 25 rows like `place;appliance_store;no_category_inverse;category`) | ⚠️ WARNING | The row exists with the right reason, but the entity is wrong and a partner could read it as an unmatchable place. Fix: divert with `entity="category"`. Does not fail the must-have ("lands in the mapping document with a reason"). |
| `src/letmegetin/application/places/lov2_export.py` | 198-206 | `stream_answers` is not gated by the place's mappability. With the committed `blocked` rule, `places.csv` is empty but `answers.csv` carries 1,702,243 rows keyed on our internal `place_id`, which no place row joins to. | ⚠️ WARNING | Latent: once the probe records `origin_id`/`slug`, imported places are keyed and the join is restored; zero user places exist today. A user-created place with no `source_id` would still orphan its answers. |
| `.planning/ROADMAP.md` | 89-106 | "Plans: 3/6 plans executed" and waves 3–5 unchecked although all six SUMMARYs exist | ℹ️ INFO | Stale bookkeeping in ROADMAP/STATE (`Plan: 3 of 6`); no code impact. |
| `.planning/phases/15-acceslibre-round-trip/15-VALIDATION.md` | 4-6 | `status: draft`, `nyquist_compliant: false`, Wave 0 unchecked | ℹ️ INFO | Validation artifact not updated after execution; the plan's automated checks are green. |
| `.planning/phases/15-acceslibre-round-trip/15-CONTEXT.md` | — | Does not record the `new-only` contributor-terms decision (it predates it) | ℹ️ INFO | Not a contradiction: D-01 (dual) stands, and the decision is recorded in 15-06-SUMMARY and 15-SECURITY AR-15-01. |

Debt-marker scan (TBD/FIXME/XXX) over the phase's touched files: none.

### Human Verification Required

#### 1. Live read-only probe (identifier rule + A2)

**Test:** With `LETMEGETIN_ACCESLIBRE_API_KEY` from LET-130, run
`scripts/with-secrets.sh uv run python -m letmegetin.admin acceslibre probe <origin_id>`.
**Expected:** Both `list_erps` lookups return (or do not return) the ERP, `get_erp` prints the real
`accessibilite` section keys, and `data/referential/acceslibre_identifier_rule.csv` records
`origin_id`/`slug`/`blocked` plus its detail.
**Why human:** The five stub tests prove the code path only; a stub cannot establish the live read
contract. Until this runs, the rule stays `blocked;UNVERIFIED`, the feed is fail-closed, and every
place diverts. Owner: **LET-130**.

#### 2. No-op PATCH on staging (A1 + write key names)

**Test:** With the same key, run `acceslibre push --dry-run` on one known place, then a single
no-op PATCH of that ERP's current value.
**Expected:** HTTP 200 with an `ErpImport` body and the value under the real `accessibilite` key
names.
**Why human:** 15-05 Task 3 is a blocking-human checkpoint; the functional push tests substitute an
in-process `FakeAccesLibre`, so A1 and the write key name are assumptions. This is the only thing
between "mechanically idempotent" and "proven against AccesLibre". Owner: **LET-130**.

#### 3. Contributor terms (feed coverage, not code)

**Test:** Ship the contribution-terms clause (a legal/product deliverable) before relying on a full
"all owned rows flow back" statement.
**Expected:** The clause records the `new-only` position (new contributions are `dual`; historical
rows are untouched).
**Why human:** No user rows exist today (`place_accessibility where source='user'` = 0), so
`new-only` and a re-stamp are indistinguishable; the decision is accepted as AR-15-01. Owner:
**LET-131**.

### Gaps Summary

No must-have is failed or missing. The phase delivers the whole mechanism: a destination-parameterised
export with a fail-closed licence gate, a pure partner projection keyed on the probe's identifier
rule, a reviewed mapping document, an operator push with typed read-then-diff, amended-D-11 freshness
and an append-only journal, and the `dual` licence that makes new contributions shippable to a lov2
destination.

Two external facts are still assumptions, and both need the AccesLibre key (LET-130): the live read
contract (A2) and the live write contract (A1). The stub/MockTransport tests are not evidence of the
live API, so the status is `human_needed`, not `passed`.

The `blocked;UNVERIFIED` identifier rule is the designed fail-closed default (T-15-05/D-05), not a
failure. Its measured consequence on the dev database (634,931 places) is: `places.csv` header-only;
`categories.csv` 133 and `criteria.csv` 8 projected; `answers.csv` 1,702,243 mirrored rows keyed on
our `place_id`; `mapping.csv` with 232 `criterion;…;not_expressible`, 133 reviewed
`category;…;canonical_activite`, 25 `no_category_inverse` category rows (mislabeled `entity=place`),
one aggregate `place;;identifier_unresolved;…634931 rows`, and the D-05 note. ATTRIBUTION lists only
`acceslibre` (no `dual` row is exported because no user answer exists).

---

_Verified: 2026-11-15T20:46:27Z_
_Verifier: the agent (gsd-verifier)_
