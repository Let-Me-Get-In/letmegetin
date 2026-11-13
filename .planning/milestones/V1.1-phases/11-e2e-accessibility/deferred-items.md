# Deferred items — Phase 11

## From plan 11-04 (found while running the e2e gate, not caused by it)

**The e2e suite can exceed the app's own public rate limit.**

- Symptom: a full `npx playwright test --project=chromium` run intermittently fails 1–5 unrelated
  read-only specs; the page snapshot shows `alert: Rate limit exceeded`, heading `0 lieu` and the
  "Aucun lieu trouvé" empty state. Three previously green specs (`search`, `pagination`, `record`) were
  hit during this plan's gate attempts.
- Cause: `rate_limit_default_rpm = 60` per IP per 60 s (`src/letmegetin/config.py`), applied to
  `/api/v1/places`. One search page load already spends several calls (100 places, categories, and
  Next.js prefetches of the visible place routes), so a 14-test run from a single IP exceeds the window
  when the suite runs in ~7–35 s. A first run after a ~70 s cooldown is fully green, every time.
- Not fixable in this plan (e2e repo only, no app config touched, and the limit is the product's own
  defence). Options, for whoever owns the next phase: a higher development limit, fewer `<Link>`
  prefetches on the results list, or `retries: 1` on the development job so a window-crossing failure
  re-runs. Raising the limit on production would be the wrong fix.
- Until then: run the gate as a first run after a cooldown, and read a failure's page snapshot before
  assuming a regression — "Rate limit exceeded" in the snapshot means the run, not the code.

## From plan 11-04 (accepted, by design)

**The human VoiceOver/NVDA pass is outstanding.** `docs/screen-reader-audit.md` and
`docs/screen-reader-audit-template.md` exist in the e2e repo; the pass itself has not been performed,
so A11Y-01 stays open after this plan. Record it in the template before marking the requirement
complete.

**The axe gate is report-only.** `AXE_STRICT` is unset in `.github/workflows/e2e.yaml`; plan 11-07
fixes the one serious finding (`link-in-text-block`, the MapLibre attribution link on the search page)
and flips the env line.

## Resolved before closure (2026-11-12)

**The human screen-reader pass is done.** VoiceOver / macOS 26.6.2 / Safari 26.6.2,
S1–S6 and R1–R6 in French and English: 12/12 pass, no finding
(`letmegetin-e2e/docs/screen-reader-audit-2026-11-11.md`). **NVDA stays unrun** —
no Windows host — recorded as `not run` in that sheet and tracked on LET-82.
A11Y-01 is satisfied on the documented VoiceOver audit.

**The axe gate is strict, not report-only.** Plan 11-07 set `AXE_STRICT: "1"` in
the development job; the paragraph above is historical.
