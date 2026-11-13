# Phase 13: Documented-place visualisation - Pattern Map

**Mapped:** 2026-11-13
**Files analyzed:** 14 (create + modify)
**Analogs found:** 14 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/letmegetin/domain/places/documentation.py` | domain (pure) | transform | `src/letmegetin/domain/referential/entities.py` | exact |
| `src/letmegetin/application/places/get_place.py` | service (use case) | transform | itself (extend `_filled_rate`/`_completion_by_family`) | exact |
| `src/letmegetin/application/places/search.py` | service (use case) | request-response | itself (extend `search_places`) | exact |
| `src/letmegetin/api/v1/places.py` | controller | request-response | itself (extend `search`, `place_detail`) | exact |
| `src/letmegetin/api/schemas/places.py` | schema | transform | itself (`PlaceSummaryOut`, `PlaceDetailOut`) | exact |
| `docs/public-api.md` | doc | — | itself (additive-field "Provenance" section) | exact |
| `tests/**` (backend ladder + endpoint) | test | — | `tests/unit/application/places/**`, `tests/functional/**` | role-match |
| `web/src/lib/types.ts` | model (TS type) | transform | itself (`PlaceSummary`, `PlaceDetail`) | exact |
| `web/src/lib/search.ts` | utility | transform | itself (`placesPath`, `familyLabel`) | exact |
| `web/src/lib/documentation.ts` (new, optional) | utility | transform | `web/src/lib/search.ts` (`familyLabel`) | exact |
| `web/src/lib/i18n.ts` | config (dict) | — | itself (`MESSAGES`, `format`) | exact |
| `web/src/app/globals.css` | config (tokens) | — | itself (`@theme`, dark block) | exact |
| `web/src/app/places/[slug]/page.tsx` | component (server) | request-response | itself (completion section) | exact |
| `web/src/components/search/place-list.tsx` | component (client) | transform | itself (card markup) | exact |

> All analogs are git-tracked source in `src/` and `web/`; no `.gsd` capability mirrors exist in this repo.

---

## Pattern Assignments

### 1. `src/letmegetin/domain/places/documentation.py` (domain, transform) — NEW

The ladder: a `Literal` slug type, a `(slug, min, max)` table, and a pure
`rate -> slug` function. Server owns slugs and bounds once (D-02); web never re-derives.

**Analog:** `src/letmegetin/domain/referential/entities.py` (lines 11–14) — the exact
"Literal + tuple constant" pattern this module mirrors:

```python
HandicapFamily = Literal["moteur", "auditif", "visuel", "mental"]
HANDICAP_FAMILIES: tuple[HandicapFamily, ...] = ("moteur", "auditif", "visuel", "mental")
```

**Pure-function analog:** `src/letmegetin/application/places/get_place.py` (lines 87–92)
`_filled_rate` — the rate is already `round(x, 3)` and feeds the ladder unchanged (D-03):

```python
def _filled_rate(tree: list[dict[str, Any]], values: dict[str, dict[str, Any]]) -> float:
    leaves = _leaf_slugs(tree)
    if not leaves:
        return 0.0
    filled = [slug for slug in leaves if slug in values and _recorded(values[slug])]
    return round(len(set(filled)) / len(leaves), 3)
```

**Shape to produce** (no SQLAlchemy, no FastAPI — domain is pure):

```python
DocumentationLevel = Literal["none", "sketch", "partial", "good", "very_good", "complete"]
DOCUMENTATION_LEVELS: tuple[DocumentationLevel, ...] = (
    "none", "sketch", "partial", "good", "very_good", "complete",
)
# (min, max) bounds per D-01; 0-based min, max as percent/100.
def documentation_level(rate: float) -> DocumentationLevel: ...
```

Bounds (D-01): `none` 0, `sketch` 0.01–0.25, `partial` 0.26–0.50, `good` 0.51–0.75,
`very_good` 0.76–0.99, `complete` 1.0. `none` is 0 (and only 0); `complete` is exactly 1.0.

---

### 2. `src/letmegetin/application/places/get_place.py` (use case, transform) — MODIFY

Adds `documentation` (overall `{rate, level}`) and a per-family level to `PlaceDetail`.

**Analog:** itself — the dataclass and both derivation helpers already here.

`PlaceDetail` dataclass (lines 21–32) gains a field (alongside `filled_rate`, line 29):

```python
@dataclass
class PlaceDetail:
    place: Place
    accessibility: list[PlaceAccessibility] = field(default_factory=list)
    accessibility_by_family: dict[str, float] = field(default_factory=dict)
    tree: list[dict[str, object]] = field(default_factory=list)
    filled_rate: float = 0.0
    # new: documentation: Documentation | None = None  (overall {rate, level})
```

`_completion_by_family` (lines 109–124) is the per-family analog — the family level is the
same loop, adding `documentation_level(score)` per family (Open Question 3: `level` sits beside
`rate` in `accessibility_by_family`):

```python
def _completion_by_family(values, criteria) -> dict[str, float]:
    satisfied = {value.criterion_slug for value in values if _recorded(value.value)}
    scores: dict[str, float] = {}
    for family in HANDICAP_FAMILIES:
        family_criteria = [
            slug for slug, criterion in criteria.items() if family in criterion.handicap_families
        ]
        scores[family] = (
            round(len(satisfied.intersection(family_criteria)) / len(family_criteria), 3)
            if family_criteria
            else 0.0
        )
    return scores
```

The overall `documentation` derives from `filled_rate` (line 54) via `documentation_level(...)`.

---

### 3. `src/letmegetin/application/places/search.py` (use case, request-response) — MODIFY

Threads a `with_documentation: bool = False` flag into `search_places` (D-07, opt-in).

**Analog:** itself — `search_places` signature (lines 24–36) already threads keyword filters:

```python
async def search_places(
    places: PlaceRepository,
    lat: float, lng: float,
    radius: float = DEFAULT_RADIUS_METRES,
    *, q: str | None = None, criterion_ids: Sequence[int] = (), family: HandicapFamily | None = None,
    category_id: int | None = None, limit: int = DEFAULT_LIMIT, offset: int = DEFAULT_OFFSET,
) -> SearchPage:
```

**Caution (planner must resolve):** `PlaceHit`/`Place` (entities, `domain/places/entities.py`
lines 30–107) carries **no** `filled_rate`; it is computed only in `get_place` from the grid
tree. Search results therefore have no rate today. To emit `documentation: {rate, level}` per
result the planner must either (a) store/join a `filled_rate` on the place, or (b) batch-compute
it for the hit set. `PlaceSummaryOut` (schemas, line 15) confirms no rate exists in search output
today. This is the one real backend gap in the phase — flag it in the plan.

---

### 4. `src/letmegetin/api/v1/places.py` (controller, request-response) — MODIFY

Adds `with_documentation` query param to `search`, and surfaces `documentation` on both endpoints.

**Analog:** itself — the `Annotated[... Query]` param pattern (lines 84–99):

```python
async def search(
    places: PlaceRepo, categories: CategoryRepo, response: Response,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius: Annotated[float, Query(gt=0, le=50_000)] = DEFAULT_RADIUS_METRES,
    q: Annotated[str | None, Query(max_length=120)] = None,
    ...
) -> list[PlaceSummaryOut]:
    page = await search_places(places, lat, lng, radius, q=q, criterion_ids=_criterion_ids(filters),
                               family=family, category_id=category_id, limit=limit, offset=offset)
    response.headers["X-Has-More"] = "true" if page.has_more else "false"
    return [PlaceSummaryOut.from_place(hit.place, hit.distance) for hit in page.hits]
```

`with_documentation` becomes `Annotated[bool, Query()] = False` and is passed through
`search_places` (D-07: absent by default so existing consumers pay nothing). The bare-JSON-array
shape is unchanged (SEARCH-03).

`place_detail` (lines 139–148) already returns `PlaceDetailOut.from_detail(detail)` — the new
`documentation` field flows through `from_detail` with no controller change beyond the schema.

---

### 5. `src/letmegetin/api/schemas/places.py` (schema, transform) — MODIFY

Adds a `DocumentationOut` model and the `documentation` field to both out-schemas.

**Analog:** itself — `PlaceSummaryOut` (lines 15–38) and `PlaceDetailOut` (lines 138–182).

`PlaceSummaryOut` gains an optional field (additive, D-07):

```python
class PlaceSummaryOut(BaseModel):
    slug: str
    name: str
    ...
    operating_status: str
    documentation: DocumentationOut | None = None   # new, absent by default

    @classmethod
    def from_place(cls, place, distance=None) -> PlaceSummaryOut:
        return cls(slug=place.slug, name=place.name, category=place.category_slug, ...,
                   operating_status=place.operating_status)
```

`PlaceDetailOut` (line 146) already carries `accessibility_by_family: dict[str, float]` — this
changes to a `{rate, level}` shape per Open Question 3, plus a top-level `documentation`. The
`from_detail` classmethod (lines 153–182) is the copy point: it already maps
`accessibility_by_family=detail.accessibility_by_family` (line 173) and `filled_rate` (line 175).

`DocumentationOut` mirrors `CandidateOut` (lines 185–200) as the smallest field-pair model:

```python
class DocumentationOut(BaseModel):
    rate: float
    level: str
```

---

### 6. `docs/public-api.md` (doc) — MODIFY

Documents `with_documentation`, the six slugs and their bounds (D-09).

**Analog:** itself — the "Provenance" additive-field section (lines 59–73), which documents an
additive, optional field without disturbing the endpoints table:

```markdown
`GET /places/{slug}` is the only read endpoint that exposes provenance. It carries three
additive, optional fields ...
```

Mirror that shape for `documentation`: a short section stating the six slugs, their bounds
(D-01), that the level is a stable enum (not display text), and that search exposes it only
under `with_documentation=true`. Update the endpoints table (lines 43–45) to mention the flag.

---

### 7. `web/src/lib/types.ts` (TS model, transform) — MODIFY

**Analog:** itself — `PlaceSummary` (lines 3–12) and `PlaceDetail` (lines 53–61).

```typescript
export type PlaceSummary = {
  slug: string;
  name: string;
  ...
  operating_status: string;
  documentation?: Documentation;   // new, optional (absent when flag off)
};

export type PlaceDetail = PlaceSummary & {
  accessibility: AccessibilityValue[];
  accessibility_by_family: Record<string, number>;   // becomes Record<string, { rate: number; level: string }>
  tree: TreeNode[];
  filled_rate: number;
  ...
};

export type Documentation = { rate: number; level: string };
```

`Documentation` follows the flat `Photo`/`Review` type style (lines 31–44).

---

### 8. `web/src/lib/search.ts` (utility, transform) — MODIFY

`placesPath` gains `with_documentation=true` (D-07).

**Analog:** itself — `placesPath` (lines 58–72):

```typescript
export function placesPath(state: SearchState, offset = 0): string {
  const params = new URLSearchParams({
    lat: String(state.lat), lng: String(state.lng), radius: String(state.radius), limit: "100",
  });
  if (state.q) params.set("q", state.q);
  ...
  if (offset > 0) params.set("offset", String(offset));
  return `/api/v1/places?${params.toString()}`;
}
```

Add `params.set("with_documentation", "true");` unconditionally (the search view always wants the
signal; it is additive and the card omits the chip when the field is absent).

---

### 9. `web/src/lib/documentation.ts` (utility, transform) — NEW (optional but recommended)

One slug→label/class map shared by the record page and the search card (D-02: web maps slug →
localized label, never re-derives). Without it the mapping is duplicated in two components.

**Analog:** `web/src/lib/search.ts` `FAMILY_KEYS` + `familyLabel` (lines 74–87) — the exact
slug→message-key pattern:

```typescript
export const FAMILY_KEYS = ["moteur", "auditif", "visuel", "mental"] as const;

const FAMILY_MESSAGE_KEYS = {
  moteur: "familyMoteur", auditif: "familyAuditif", visuel: "familyVisuel", mental: "familyMental",
} as const;

export function familyLabel(family: string, locale: Locale = "fr"): string {
  const key = FAMILY_MESSAGE_KEYS[family as keyof typeof FAMILY_MESSAGE_KEYS];
  return key ? t(locale, key) : family;
}
```

Mirror with `DOC_LEVELS` (six slugs in order), `levelLabel(slug, locale)`, `levelMeaning(slug,
locale)`, and `levelChipClass(slug)` (returns the Tailwind class string from UI-SPEC's
"Level → class mapping" table). The `FAMILY_KEYS` constant here is also what the record page
uses for family order (UI-SPEC: "not `Object.entries`").

---

### 10. `web/src/lib/i18n.ts` (config/dict) — MODIFY

Adds level labels, meanings, legend and banner keys to `fr` and `en` only (Open Question 1:
`Locale` stays `"fr" | "en"`).

**Analog:** itself — `MESSAGES` structure (lines 20–428), and the `format` var-substitution
(lines 453–457) for `docValueText`:

```typescript
export function format(message: string, vars: Record<string, string | number>): string {
  return message.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
    name in vars ? String(vars[name]) : placeholder,
  );
}
```

New flat keys (UI-SPEC "Copywriting Contract"): `docNone` … `docComplete`, `docLegendHeading`,
`docLegendIntro`, `docValueText` (`"{level}, {percent} %"` fr / `"{level}, {percent}%"` en),
`docUndocumentedTitle`, `docUndocumentedBody`, `docBannerCta`. There are **no** `docMeaning*` keys:
the revised contract dropped the per-level meaning sentences. `completeThisRecord` is the h2 of the
contribution section and must not be reused for the banner link. Two existing keys **are** edited
with their e2e selectors in the same change: `criteriaHaveValue` (no-break space before `%`) and
`reviewCountLine` (percent clause removed).

---

### 11. `web/src/app/globals.css` (config/tokens) — MODIFY

Adds `--color-doc-*` ramp tokens, light and dark (UI-SPEC lines 55–73).

**Analog:** itself — `@theme` (lines 3–14) and the dark block (lines 16–26):

```css
@theme {
  --color-paper: #f7f4ec;
  --color-accent: #1f6f4a;
  --color-line: #d8ddd4;
  ...
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-paper: #101613;
    --color-accent: #7fd1a6;
    ...
  }
}
```

Add exactly FOUR tokens — `--color-doc-sketch`, `--color-doc-partial`, `--color-doc-good`,
`--color-doc-very-good` — in `@theme` (light hexes) and override in the dark `:root` block (dark
hexes), matching the existing token pattern. Do not declare `doc-none` or `doc-complete`: `none`
uses `line`/`muted` and `complete` uses `accent`, so they would be dead tokens. Values from the
UI-SPEC "Documentation Ladder — Visual Tokens" table (chip background column).

---

### 12. `web/src/app/places/[slug]/page.tsx` (server component, request-response) — MODIFY

Rewrites the completion section: overall level heading, family chips, legend, empty banner.

**Analog:** itself — the completion section (lines 117–145):

```tsx
<section aria-labelledby="completion">
  <h2 id="completion" className="text-xl font-semibold">{t(locale, "completion")}</h2>
  <div className="mt-3 space-y-2">
    <div role="progressbar" aria-valuenow={filledPercent} aria-valuemin={0}
         aria-valuemax={100} aria-label={t(locale, "completion")}
         className="h-3 overflow-hidden rounded-full bg-line">
      <div className="h-full bg-accent" style={{ width: `${filledPercent}%` }} />
    </div>
    <p className="text-sm text-muted">
      {format(t(locale, "criteriaHaveValue"), { percent: filledPercent })}
    </p>
  </div>

  <dl className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
    {Object.entries(place.accessibility_by_family).map(([family, score]) => (
      <div key={family} className="rounded-card border border-line px-3 py-2">
        <dt className="text-sm text-muted">{familyLabel(family, locale)}</dt>
        <dd className="text-lg font-medium">{Math.round(score * 100)}%</dd>
      </div>
    ))}
  </dl>
</section>
```

`filledPercent` is already `Math.round(place.filled_rate * 100)` (line 83). Changes per UI-SPEC
(lines 179–269): insert an `h3#doc-overall` level-name heading; add `aria-valuetext` to the
progressbar; switch `Object.entries` → `FAMILY_KEYS.map`; change the `dd` to a level chip +
percentage; add the legend `<dl>`; add the `doc-undocumented` banner (rendered when level is
`none`, placed after `<VerifyBanner />` line 115). `familyLabel` import already present (line 15).

---

### 13. `web/src/components/search/place-list.tsx` (client component, transform) — MODIFY

Adds the level chip to each card (no border tint: the revised contract removed it).

**Analog:** itself — the card `Link` (lines 36–61), including the existing border-precedence
logic and the operating-status pill:

```tsx
<Link
  href={`/places/${place.slug}`}
  onMouseEnter={() => onSelect(place.slug)}
  onFocus={() => onSelect(place.slug)}
  className={`block rounded-card border p-4 transition-colors ${
    place.slug === selected
      ? "border-accent bg-accent-soft/50"
      : "border-line bg-white/60 hover:border-accent dark:bg-white/5"
  }`}
>
  ...
  {place.operating_status !== "open" ? (
    <span className="mt-2 inline-block rounded-full bg-warn/10 px-2 py-0.5 text-xs text-warn">
      {place.operating_status === "duplicate_review" ? t(locale, "possibleDuplicate") : place.operating_status}
    </span>
  ) : null}
</Link>
```

Per UI-SPEC ("Search Result Card"): the card's border, hover and selected styles are untouched.
A new meta row (level chip + existing status pill)
uses `flex flex-wrap items-center gap-2 mt-2`; the chip is `inline-flex items-center rounded-full
px-3 py-1 text-sm font-semibold` with the `levelChipClass(slug)` text, rendered only when
`place.documentation` is present.

---

### 14. Tests (backend + web)

**Backend analog:** the ladder is a pure function → unit test beside it (mirror
`tests/unit/application/places/**` layout); endpoint wiring goes in `tests/functional/**`
(real API against PostGIS). Assert: six slugs, bounds per D-01, `none` only at 0, `complete` only
at 1.0, `with_documentation` absent by default and present when requested.

**Web analog:** `web/src/lib/search.test.ts` (lines 33–58) shows the `placesPath` assertion style:

```typescript
it("builds the places URL with the active filters", () => {
  const path = placesPath({ ...DEFAULT_SEARCH, q: "hôtel", family: "moteur", category: "pharmacy", criteria: [7] });
  expect(path).toContain("/api/v1/places?");
  expect(path).toContain("q=h%C3%B4tel");
});
```

Add an assertion that `placesPath` contains `with_documentation=true`. Per UI-SPEC
(Verification Gates, line 446): a test asserts the level map covers all six slugs and the family
order is `FAMILY_KEYS`. `i18n.test.ts` (`web/src/lib/i18n.test.ts`) is the analog for the
"every new key present in fr and en" check.

---

## Shared Patterns

### Rate → level is server-owned, web maps slug only (D-02)
**Source:** `src/letmegetin/domain/places/documentation.py` (new) + `web/src/lib/documentation.ts` (new).
**Apply to:** backend (get_place, search, schemas) and web (page, place-list).
The web never computes a level from a rate; it only maps the slug the server returns.

### Additive optional field (D-07, mirrors Provenance precedent)
**Source:** `docs/public-api.md` lines 59–73; `PlaceSummaryOut` optional fields (schemas lines 15–38).
**Apply to:** `PlaceSummaryOut.documentation` (absent by default), `PlaceDetailOut.documentation`.
Existing consumers pay nothing; the bare JSON array shape is unchanged.

### No French literals outside i18n.ts (`check:i18n` gate)
**Source:** `web/src/lib/i18n.ts` line 8–10 (single owner of messages) + `familyLabel` map pattern.
**Apply to:** the record page, place-list, and the new `documentation.ts`. The call site uses a
key, never a literal; the `fr` column stays byte-identical to existing e2e-selected strings.

### Token naming and dark-mode override
**Source:** `web/src/app/globals.css` lines 3–26 (`--color-*` in `@theme` + dark `:root`).
**Apply to:** the six `--color-doc-*` tokens.

---

## Caution / Planner-visible Gap

**Search has no `filled_rate` today.** `Place` (`domain/places/entities.py` lines 30–61) and
`PlaceSummaryOut` (`schemas/places.py` lines 15–38) expose no rate; `filled_rate` is computed
only in `get_place` (line 54) from the grid tree. D-07 requires `documentation: {rate, level}`
per search result under `with_documentation=true`. The planner must choose how search obtains the
rate: store a `filled_rate` on the place (new column/migration — but D-03 says "no new column"),
or batch-compute it for the hit set (a join over the grid + accessibility values). This is the
one decision PATTERNS.md cannot resolve from an existing analog; surface it explicitly in the
PLAN so the executor does not invent a divergent path.

---

## Metadata

**Analog search scope:** `src/letmegetin/domain/**`, `src/letmegetin/application/**`,
`src/letmegetin/api/**`, `docs/`, `web/src/**`.
**Files scanned:** 18 (entities, get_place, search, places.py, schemas, public-api, types, search,
i18n, globals.css, labels, place-list, search-view, page.tsx, search.test.ts, families.py,
coverage.py, entities referential).
**Pattern extraction date:** 2026-11-13
