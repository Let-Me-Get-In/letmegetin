---
phase: "14"
slug: "open-odbl-export"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-15"
---

# Phase 14 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| operator CLI → DB | `place history` reads journal payloads already held in the DB; no untrusted input crosses | provenance already public |
| writer → journal | `export_event` captures full row state in the same transaction as the write | place and answer rows |
| DB → export files | the export serialises rows the DB holds; the licence matrix is the gate that must not leak a withheld row | public place/answer data |
| CLI/host → filesystem | `--out` / the served volume; a write must never escape the export directory | ZIPs, `latest.json` |
| retention → journal | the prune deletes journal events and delta ZIPs; it must never delete what the current snapshot needs | journal rows, archive names |
| client → API | `{name}` is untrusted path input that must never escape `export_dir` | archive name |
| Actions runner → host | `workflow_dispatch` SSHes to the host; only the SSH key/host pair crosses | SSH credentials |
| doc → partner | `docs/public-api.md` is the partner contract and must not over-claim | prose |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-14-01 | Tampering | `_append_export_event` and the write paths | high | mitigate | Append in the caller's unit of work, flush only; rejections journal only when the row mutates; AST census test fails any new `PlaceModel` writer that does not journal (`tests/unit/infrastructure/persistence/test_export_event_chokepoints.py`) | closed |
| T-14-02 | Information Disclosure | `letmegetin-admin place history` | low | accept | Operator-only CLI, no public route; payloads repeat provenance already stored | closed (accepted) |
| T-14-03 | Tampering | dependency installs | high | mitigate | No package added this phase; lockfiles unchanged | closed |
| T-14-04 | Tampering | `_answer_may_leave` answer filter | high | mitigate | `EXISTS` on `licence_destination.allowed`, applied inside the ranked CTE before the winner pick; a denied answer is absent **and** counted; reconciliation test | closed |
| T-14-05 | Information Disclosure | exported provenance columns | low | accept | Intentional and already public through the detail endpoint | closed (accepted) |
| T-14-06 | Tampering | dependency installs | high | mitigate | stdlib only (`csv`, `zipfile`, `json`, `fcntl`) | closed |
| T-14-07 | Tampering | `GET /export/{name}.zip` | high | mitigate | Name allow-list before any FS call, then resolved-path containment and `is_file()`; 9 traversal URLs, a real out-of-directory symlink, and helper-level raw encodings all assert non-200 with marker absence | closed |
| T-14-08 | Information Disclosure | `export_data` volume | medium | mitigate | Only `latest.json`, `*.zip`, the lock and transient `.tmp` are written; no secret reaches the directory; Caddy unchanged; API mount read-only | closed |
| T-14-09 | Tampering | dependency installs | high | mitigate | No package added | closed |
| T-14-10 | Information Disclosure | `docs/public-api.md` | low | accept | Public by design; wording constrained to the reviewed constants | closed (accepted) |
| T-14-11 | Tampering | dependency installs | high | mitigate | No package added; OpenAPI regenerated deterministically | closed |
| T-14-12 | Tampering | `_guard_csv_cell` formula injection | medium | mitigate | Guard applied per column against `FREE_TEXT_COLUMNS`; negative longitudes, `+33` phones and the header are asserted untouched | closed |
| T-14-13 | Tampering | `.github/workflows/export-odbl.yml` SSH | high | mitigate | `workflow_dispatch` only, action pinned by SHA, `permissions: contents: read`, only `DEPLOY_*` secrets, host key fingerprint variable, DB/API secrets resolved on the host by `with-secrets.sh` | closed |
| T-14-14 | Tampering | `scripts/export-odbl.sh` mode argument | medium | mitigate | `case snapshot\|delta`, everything else exits 2; fixed `--out`; argv test in both modes, coupled to the script | closed |
| T-14-15 | Tampering | dependency installs | high | mitigate | bash + systemd only | closed |
| T-14-16 | Tampering | retention prune | high | mitigate | Inside the export `flock`, only after a snapshot completes, events pruned to the **previous** boundary, delta ZIPs only when `to_seq <= current snapshot`, only unlisted orphans removed; tests prove two-cycle keep, no prune on failure, snapshots kept | closed |
| T-14-17 | Tampering | `safe_seq()` MVCC boundary | high | mitigate | `max(seq) WHERE xid < pg_snapshot_xmin(pg_current_snapshot())`, first statement of the REPEATABLE READ transaction; test holds a transaction open, then commits and asserts the next delta emits it | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-14-01 | T-14-02 | The journal repeats provenance already held in the DB; `place history` is operator-only and has no public endpoint this phase (D-13) | operator | 2026-11-15 |
| AR-14-02 | T-14-05 | `source`, `source_licence`, `source_url` and dates are the point of the export and are already public in the place detail | operator | 2026-11-15 |
| AR-14-03 | T-14-10 | The public contract has to be public; the risk is a wording error, mitigated by sharing the constants with `attribution.py` | operator | 2026-11-15 |

*Accepted risks do not resurface in future audit runs.*

---

## Residual Observations

Not declared mitigations and not open at the block threshold:

1. `SqlAlchemyPlaceRepository.update()` journals unconditionally, so a future no-op `update()` would append an event. No production caller exists; the consequence is journal bloat, not a missing event.
2. The REPEATABLE READ isolation is asserted by wiring (`Session.connection(execution_options=…)` before the first statement), not observed with `SHOW transaction_isolation` inside the export transaction.
3. `website`, `phone`, `source_url`, `slug`, `origin_id` and `criterion_slug` are free text **outside** `FREE_TEXT_COLUMNS`. Nothing user-typed reaches them today (contributions write JSON values only; places come from the reviewed importer), so the CSV guard cannot be bypassed by a user — but a hostile upstream dataset would reach the cell unguarded.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-15 | 17 | 17 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-15
