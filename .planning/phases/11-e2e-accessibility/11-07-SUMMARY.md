# Plan 11-07 — close the axe findings and make the gate strict

**Status:** complete (machine-checkable half). A11Y-01 stays open for the human pass.
**Repos:** `letmegetin` (app fix) + `letmegetin-e2e` (gate flip).

## What the report actually contained

Plan 11-04's artifact held exactly **one** serious/critical row, not the
structural inventory the plan's `files_modified` anticipated:

| Page | Rule | Impact | Node |
|---|---|---|---|
| search | `link-in-text-block` (WCAG 1.4.1) | serious | `a[href$="maplibre.org/"]`, contrast 2.02:1, `text-decoration: none` |

That is MapLibre's own attribution control. Colour is its only distinction from
the surrounding text, and at 2.02:1 it does not carry 1.4.1. No component
change was needed — one CSS rule was the whole fix.

## Files actually touched

`web/src/app/globals.css` only. The plan's plausible list (`layout.tsx`,
`site-header.tsx`, `search-view.tsx`, `place-list.tsx`, `map-view.tsx`,
`filters.tsx`, `accessibility-tree.tsx`, `review-list.tsx`) was **not** needed:
none of those files appears in the artifact.

## The rule, and why it needed a second attempt

```css
.maplibregl-ctrl-attrib a:link,
.maplibregl-ctrl-attrib a:visited {
  text-decoration: underline;
}
```

The first attempt used the plain `.maplibregl-ctrl-attrib a` selector and did
**not** take effect: MapLibre ships an equal-specificity rule
(`color: rgba(0,0,0,.75); text-decoration: none`) that loads after the global
sheet and won the cascade. Confirmed on the live page —
`decoration: "none"` while both rules were present. The pseudo-classes lift the
specificity to `(0,2,1)` against the vendor's `(0,1,1)`, so no `!important` is
needed. After the fix the computed style reads `decoration: "underline"`.

## Verification (real)

```
cd web && npm run lint          → check:i18n: 24 files scanned, no French literal.
cd web && npm run typecheck     → clean
cd web && npm test -- --run     → 8 files, 44 tests passed
cd web && npm run build         → compiled

# against dev at 0bfad02
E2E_BASE_URL=https://app.dev.letmegetin.org AXE_STRICT=1 \
  npx playwright test a11y.spec.ts --project=chromium
  ✓ records axe violations on the search page
  ✓ records axe violations on a record page
  2 passed

test-results/axe-violations.json → seriousCriticalCount: 0, violations: []
```

## The gate

`.github/workflows/e2e.yaml`, development job only:

```yaml
AXE_STRICT: "1"
```

with a comment naming the local invocation. The production job still leaves
`AXE_STRICT` unset — a nightly red run is a signal, not a merge block, the same
shape as the `E2E_REQUIRE_AUTH` split. Parsed and confirmed: `development` has
`AXE_STRICT=1`, `production` has none.

## Commits

| Repo | Commit | PR |
|---|---|---|
| app | `0bfad02` `fix(a11y): underline the map attribution link (LET-35)` | #39 |
| e2e | `20f67ad` `ci(e2e): enforce strict axe gate on serious/critical (LET-35)` | #4 |

## What is still open

**The human VoiceOver/NVDA pass.** This plan fixes what axe can see; it does
not and cannot perform A11Y-01's screen-reader audit. `docs/screen-reader-audit.md`
carries the protocol and the blank results sheet, and the runbook states the
pass is not yet performed. A11Y-01 must not be marked complete until a person
fills that sheet in.

## Deviations

1. **One file, not eight.** The plan's `files_modified` was a guess made before
   the artifact existed; the real finding was a single third-party control.
2. **Two attempts on the CSS rule.** The equal-specificity override is recorded
   above because it is the kind of thing that silently ships as a no-op — the
   strict scan failed the first time, which is exactly the gate working.
3. **Verification required a branch deploy.** The scan runs against the deployed
   app, so dev was deployed from the branch SHA (`126472d`, then `0bfad02`)
   before the strict run could observe the fix.
