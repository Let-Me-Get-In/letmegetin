---
status: testing
phase: 15-acceslibre-round-trip
source: [15-01-SUMMARY.md, 15-02-SUMMARY.md, 15-03-SUMMARY.md, 15-04-SUMMARY.md, 15-05-SUMMARY.md, 15-06-SUMMARY.md]
started: 2026-11-15T21:00:00Z
updated: 2026-11-15T21:00:00Z
---

## Current Test

number: 1
name: Partner feed lands outside the served directory
expected: |
  `admin export odbl --destination lov2_partner --out /tmp/uat15` writes the
  partner archive plus a `mapping.csv` sidecar, and leaves the public ODbL
  directory untouched.
awaiting: user response

## Tests

### 1. Partner feed lands outside the served directory
expected: The partner archive and its mapping sidecar go to `--out`; the served directory is not written.
result: pass
observed: "`lov2_partner-20261115T205731799662Z-full.zip` (6.1 MB) + `mapping.csv` (35 KB) + `latest.json` in /tmp/uat15."

### 2. A partner archive cannot be published in the served directory
expected: Pointing `--out` at the served export directory is refused with a clear error, not silently accepted.
result: pass
observed: "exit 1 — `--out points at the served export directory: a lov2_partner archive must not be published there`."

### 3. The licence matrix knows `dual`
expected: `licences audit` is clean and the matrix allows `dual` to a lov2 partner while still denying `odbl` and `cdla`.
result: pass
observed: "`licences ok: every licence has a full matrix and every row resolves`; lov2_partner: dual allowed, lov2 allowed, odbl denied (LIC-03), cdla denied."

### 4. The mapping document labels a category as a category
expected: Rows for categories carry `entity=category` and the reason, not `entity=place`.
result: pass
observed: "232 `criterion`, 158 `category`, 1 `place` aggregate, 1 `note`; first rows read `category;accounting;canonical_activite;Comptable expert-comptable (139 places)`."

### 5. Feed is fail-closed while the identifier rule is unverified
expected: With the committed `blocked;UNVERIFIED` rule, `places.csv` is a header only and every place is diverted to the mapping document rather than keyed on a guessed identifier.
result: pass
observed: "`places.csv=0`, `aliases.csv=0`, one aggregate `place;;identifier_unresolved;…` row. Correct by design (D-05), not a failure."

### 6. Answers are shipped without their places
expected: A partner archive never carries an answer whose place is absent from `places.csv`.
result: issue
reported: "`answers.csv` holds 1 702 243 rows while `places.csv` is header-only — every one references a `place_id` the archive does not define. A partner cannot join them, so the archive is unusable as delivered. Already ticketed as LET-132, but it is the current observable output."
severity: major

### 7. Push refuses to run without a key
expected: `acceslibre push --dry-run` stops with an actionable message and a non-zero exit before building any client.
result: pass
observed: "exit 1 — `no AccesLibre API key: set LETMEGETIN_ACCESLIBRE_API_KEY (see 15-PARTNER-ASK.md)`."

### 8. Probe never calls AccesLibre unauthenticated
expected: `acceslibre probe <slug>` refuses without a key instead of sending an anonymous request.
result: pass
observed: "exit 1 — `error: LETMEGETIN_ACCESLIBRE_API_KEY is not set; the probe never calls AccesLibre unauthenticated`."

## Summary

total: 8
passed: 7
issues: 1
pending: 0
skipped: 0

## Gaps

- gap_id: G-15-6
  truth: "A partner archive never carries an answer whose place is absent from places.csv."
  status: failed
  reason: "Measured: answers.csv 1 702 243 rows, places.csv header-only. The archive cannot be joined as delivered."
  severity: major
  test: 6
  artifacts: [src/letmegetin/application/places/lov2_export.py]
  missing: ["gate stream_answers on the exported place set", "count the diverted answers in the manifest"]
  tracked_as: LET-132
