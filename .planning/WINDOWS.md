---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 0
total_count: 2
last_updated: 2026-11-08T08:24:27.498Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 11 | unmet-truth |  |  | A11Y-01: the human VoiceOver/NVDA screen-reader pass is outstanding — protocol + blank template exist in the e2e repo, the pass is not performed | open |  | 2026-11-08T08:24:27.418Z |  |
| 2 | 11 | unrun-verify | letmegetin-e2e/tests/a11y.spec.ts |  | The axe gate is report-only (AXE_STRICT unset); one serious finding (link-in-text-block, MapLibre attribution link) blocks only after the app-repo fix flips it | open |  | 2026-11-08T08:24:27.498Z |  |

````json
[
  {
    "id": 1,
    "kind": "unmet-truth",
    "phase": "11",
    "file": "",
    "line": null,
    "description": "A11Y-01: the human VoiceOver/NVDA screen-reader pass is outstanding — protocol + blank template exist in the e2e repo, the pass is not performed",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-11-08T08:24:27.418Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 2,
    "kind": "unrun-verify",
    "phase": "11",
    "file": "letmegetin-e2e/tests/a11y.spec.ts",
    "line": null,
    "description": "The axe gate is report-only (AXE_STRICT unset); one serious finding (link-in-text-block, MapLibre attribution link) blocks only after the app-repo fix flips it",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-11-08T08:24:27.498Z",
    "resolved_at": null,
    "milestone": null
  }
]
````
