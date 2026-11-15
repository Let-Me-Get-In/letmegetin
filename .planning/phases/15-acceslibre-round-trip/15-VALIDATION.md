---
phase: "15"
slug: "acceslibre-round-trip"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-15"
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.2+ with pytest-asyncio (`asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`); kind tagging by folder in `tests/conftest.py` |
| **Quick run command** | `uv run pytest -m unit -q` |
| **Full suite command** | `uv run pytest -q` (functional needs PostGIS on `localhost:55433`) |
| **Estimated runtime** | ~20 s unit, ~3 min full |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -m unit -q`
- **After every plan wave:** Run `uv run pytest -m "unit or integration" -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Task IDs are assigned by the planner; this map is keyed on requirement until then.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| — | — | — | PART-01 | — | Only `lov2`/`dual` rows leave; ODbL and CDLA never do | unit + functional | `uv run pytest tests/functional/places/test_lov2_export.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | PART-01 | — | Rows carry their identifier; no identifier never enters the feed | unit | `uv run pytest tests/unit/domain/places/test_lov2_projection.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | PART-01 | — | Partner archive is outside the served export dir; `latest.json` untouched | functional | `uv run pytest tests/functional/places/test_lov2_export.py::test_partner_archive_not_served -x` | ❌ W0 | ⬜ pending |
| — | — | — | PART-01 | — | Mapping document names every unmappable place; loader fails closed on a gap | functional | `uv run pytest tests/functional/places/test_lov2_export.py::test_mapping_document_names_every_unmappable_place -x` | ❌ W0 | ⬜ pending |
| — | — | — | PART-02 | T-15-01 | Freshness: user answer uses `recorded_at`; newer remote value is skipped and journaled | unit | `uv run pytest tests/unit/domain/places/test_acceslibre_push.py::test_freshness_uses_recorded_at_for_user_answers -x` | ❌ W0 | ⬜ pending |
| — | — | — | PART-02 | T-15-02 | Only `value` leaves; never `user_id` or journal internals | unit | `uv run pytest tests/unit/domain/places/test_acceslibre_push.py::test_payload_has_no_user_id -x` | ❌ W0 | ⬜ pending |
| — | — | — | PART-02 | T-15-03 | API key never logged, host fixed to the AccesLibre origin | integration | `uv run pytest tests/integration/acceslibre/test_client.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | PART-02 | — | `--dry-run` writes nothing; replay is idempotent; every decision journaled | functional | `uv run pytest tests/functional/places/test_acceslibre_push.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | PART-02 | — | Import cannot overwrite a user row (existing provenance path) | functional | `uv run pytest tests/functional/places/test_provenance_conflict.py -x` | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/domain/places/test_lov2_projection.py` — PART-01 projection, identifier and category-inverse rules
- [ ] `tests/unit/domain/places/test_acceslibre_push.py` — PART-02 diff, freshness, payload, value validation
- [ ] `tests/integration/acceslibre/test_client.py` + `fakes.py` — `httpx.MockTransport` stub, 401/403/429, key redaction
- [ ] `tests/functional/places/test_lov2_export.py` — real PostGIS, licence predicate, unserved archive
- [ ] `tests/functional/places/test_acceslibre_push.py` — dry-run, replay idempotency, journal rows
- [ ] `tests/functional/test_licence_migration.py` — the `dual` re-stamp
- [ ] Settings field `acceslibre_api_key` monkeypatched in fixtures; no real key ever read

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| First real GET/PATCH against AccesLibre | PART-02 | No API key exists yet (D-13); the first live call is a blocking human checkpoint | Run `--dry-run` against staging, inspect the diff, then one real push on a single place |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
