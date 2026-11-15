---
phase: "15"
slug: "acceslibre-round-trip"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-15"
---

# Phase 15 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| DB → partner archive | the lov2 feed is the phase 14 writer with `destination = lov2_partner`; the licence matrix is the gate | places, answers, mapping rows |
| operator CLI → filesystem | `--out` is operator-chosen; a partner archive must never land in the public directory | ZIP, `latest.json`, `mapping.csv` |
| our DB → AccesLibre API | one GET then one PATCH per place; the payload is derived from an answer value only | accessibility values |
| AccesLibre API → us | their ERP body carries `updated_at` and their own field values | foreign data |
| code → log | the API key must never appear in an error, a traceback or a manifest | API key |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-15-01 | Information Disclosure | partner archive location | high | mitigate | Written only under the required `--out`; the public route reads `settings.export_dir` only; a functional test asserts the partner ZIP is not served, the public `latest.json` is untouched and `GET /api/v1/export/{partner}.zip` answers 404. The CLI now **refuses an `--out` that resolves to the served directory** for any non-`open_export` destination | closed |
| T-15-02 | Information Disclosure | `_licence_allows(licence, "lov2_partner")` | high | mitigate | One gate, no new branch: applied to places, to answers (both the answer and its place licence) and to the push stream; `odbl` and `cdla` rows are asserted absent from the feed **and** counted in the manifest | closed |
| T-15-03 | Information Disclosure | AccesLibre client origin | high | mitigate | The origin is a module constant, not a setting; `verify=True`, `follow_redirects=False`; a test asserts the base URL is the constant and that no other `acceslibre_*` setting exists | closed |
| T-15-04 | Information Disclosure | adapter errors and logs | high | mitigate | Errors carry slug and status only; a transport failure repeats only the exception type; no logging in the adapter or the push path; Sentry is never initialised for the CLI, and its scrubber strips the request anyway | closed |
| T-15-05 | Tampering | `acceslibre_identifier_rule.csv` | high | mitigate | Only the probe writes the rule; the loader refuses anything but exactly one rule; `blocked` returns `None` and the committed default is `blocked;UNVERIFIED`, so nothing keys on an unverified identifier | closed |
| T-15-06 | Tampering | lov2 projection (identifier + category) | high | mitigate | An unresolved identifier diverts the place to the mapping document, never a guessed key; a missing category inverse diverts; `canonical_activites` is max-places with a hard failure on a malformed row; an answer outside `FIELD_MAP` is `not_expressible` | closed |
| T-15-07 | Tampering | `validate_value` before PATCH | high | mitigate | Out-of-type, out-of-range and out-of-enum values raise and are journaled `skipped`; values are validated again inside `push_payload`, so a null that their API would apply as a deletion can never leave | closed |
| T-15-08 | Tampering | read-then-diff and freshness | high | mitigate | No blind PATCH path exists; a field differs only after typed normalisation; their `updated_at` newer than our `recorded_at` skips and journals; our null is never sent | closed |
| T-15-09 | Information Disclosure | outbound payload and feed rows | high | mitigate | The payload comes from `value["value"]` alone; feed answers carry the value only; tests assert no `user_id`/`actor`/journal key reaches either surface | closed |
| T-15-10 | Repudiation / DoS | push idempotency | medium | mitigate | Idempotency is the diff itself; the journal is insert-only with a decision CHECK and keeps the losing value; a replay patches nothing and adds no accepted row | closed |
| T-15-11 | Tampering / legal | contribution re-licensing | high | mitigate | The `checkpoint:decision` was answered **`new-only`**, so no `0016` re-stamp migration exists and no code re-stamps `source_license`. The gate held; nothing was re-licensed retroactively | closed (decision) |
| T-15-SC | Tampering | dependency install | high | mitigate | No package added this phase; `httpx` moved from the dev group to runtime dependencies, nothing new | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-15-01 | T-15-11 | The `new-only` decision leaves historical user answers on `odbl`, which the matrix forbids to `lov2_partner`. The alternative — re-stamping rows whose contributors were never told the terms — was judged worse than a narrower feed. Reversible only by a contribution-terms clause plus a reviewed migration (LET-131) | operator | 2026-11-15 |

*Accepted risks do not resurface in future audit runs.*

---

## Residual Observations

Not declared mitigations and not open at the block threshold:

1. **The partner PATCH happens before the run's single commit** (T-15-10). A crash in that window loses the `accepted` journal rows while their side already holds the value; a replay then sees equality and journals nothing. Inherent to one commit per run; the replay is still correct, only the audit trail is thin.
2. `place_id` appears in the partner feed, as it already does in the public export. It is an anonymous autoincrement id, not a user identifier.
3. **PART-02 is unverified against the live service** — A1 (a PATCH returning 200 with an `ErpImport`) and the real `accessibilite` key names are still assumptions, gated on LET-130.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-15 | 12 | 12 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-15
