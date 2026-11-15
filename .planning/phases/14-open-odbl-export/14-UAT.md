---
status: testing
phase: 14-open-odbl-export
source: [14-01-SUMMARY.md, 14-02-SUMMARY.md, 14-03-SUMMARY.md, 14-04-SUMMARY.md, 14-05-SUMMARY.md]
started: 2026-11-15T09:20:00Z
updated: 2026-11-15T09:40:00Z
---

## Current Test

<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Fresh snapshot export
expected: |
  `admin export odbl --out /tmp/uat14` writes one ZIP plus latest.json,
  reports the per-file counts, and completes in under a minute against
  634 931 places / 1 711 095 answers.
awaiting: user response

## Tests

### 1. Fresh snapshot export
expected: One ZIP + latest.json written; counts reported; ~45 s on the full dev dataset.
result: pass
observed: "export-20261115T091208546318Z-full.zip, 54,989,029 bytes in 43.7 s; places.csv=629473, categories=158, criteria=61, answers=1702243, aliases=5458; excluded answers acceslibre/lov2 = 8852."

### 2. ZIP contents are the seven contracted files
expected: places, categories, criteria, answers, aliases, ATTRIBUTION.txt, manifest.json — nothing else.
result: pass
observed: "7 entries; 442 MB uncompressed. manifest.json carries schema_version 1.0, the seven counts, the exclusion counters and the attribution text."

### 3. CSV integrity
expected: Header row, no BOM, embedded quotes escaped, negative longitude intact, dates present.
result: pass
observed: "`place_id,origin_id,slug,…` header; first bytes are `pla` (no BOM); answers value is a properly quoted JSON object; lng=2.319545 and -4.x style values unguarded; date column populated."

### 4. Attribution names only the sources actually exported
expected: ATTRIBUTION.txt lists AccesLibre with its legal licence name and the update date, the Produced Works sentence, and no OSM/Overture line.
result: pass
observed: "`acceslibre — Licence Ouverte v2.0 (Etalab 2.0) — 2026-11-13 — « Source » : …`, then the Produced Works sentence, then the forward-looking sentence. No OSM, no Overture. Same text in manifest.attribution."

### 5. Read-only routes serve the archive
expected: `/api/v1/export/latest.json` returns the pointer as JSON; `/api/v1/export/<name>.zip` returns `application/zip`.
result: pass
observed: "latest.json 200 application/json; zip 200, application/zip, 54,989,029 bytes."

### 6. Path traversal and dotfiles are refused
expected: `..`, encoded `..`, dot files and unknown names all answer 404, never a file.
result: pass
observed: "`../etc/passwd.zip` 404, `..%2Fsecret.zip` 404, `.hidden-dotfile.zip` 404, `nope.zip` 404."

### 7. Malformed archive name with a null byte
expected: A name carrying a NUL byte is refused like any other invalid name — 404, no filesystem access.
result: pass
reported: "First run: `GET /api/v1/export/x%00.zip` returned 500 (`ValueError: lstat: embedded null character in path`). Fixed in LET-128: `_is_servable` now requires `filename.isprintable()`; re-checked live, 404."
severity: major
resolved_by: LET-128

### 8. Delta keeps the snapshot pointer
expected: `--delta` writes a delta ZIP, appends a `{name, from_seq, to_seq}` entry to `latest.json.deltas`, and leaves `snapshot` and `watermark` untouched.
result: pass
observed: "delta-20261115T091321985964Z.zip; deltas[] gained `{from_seq: 0, to_seq: 0}`; snapshot still points at the full ZIP; watermark 0."

### 9. `--since` below the retention floor is refused
expected: A catch-up older than the retained journal stops with a message naming the floor and the snapshot to restart from.
result: pass
observed: "`--since -5 is below the retention floor 0: the journal before it was pruned. Restart from the snapshot 'export-…-full.zip' (seq 0).`"

### 10. Per-place history starts at the journal
expected: `admin place history <slug>` explains that a place has no history yet rather than printing an empty table.
result: pass
observed: "`no history yet for item-ea792211`, exit 0."

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0

## Gaps

- gap_id: G-14-7
  truth: "A malformed archive name carrying a NUL byte is refused like any other invalid name — 404, no filesystem access."
  status: resolved
  resolved_by: LET-128
  reason: "User-run UAT: `GET /api/v1/export/x%00.zip` returned 500 (`ValueError: lstat: embedded null character in path`) because `_is_servable` accepts control characters and `Path.resolve()` then raises."
  severity: major
  test: 7
  artifacts: [src/letmegetin/api/v1/export.py]
  missing: ["`_is_servable` rejects non-printable characters", "a functional case for `%00` asserting 404"]
