# Phase 12: Licence provenance - Pattern Map

**Mapped:** 2026-11-13
**Files analyzed:** 20 (new/modified)
**Analogs found:** 20 / 20

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/letmegetin/infrastructure/persistence/models.py` — `PlaceModel` (+`source_license`, `source_url`, `retrieved_at`) | model | CRUD | `PlacePhotoModel.license` (331) | exact |
| `src/letmegetin/infrastructure/persistence/models.py` — `PlaceAccessibilityModel` (+`source`, `source_license`, `observed_at`, `recorded_at`, `actor`) | model | CRUD | `PlaceMergeLogModel` (284) | role-match |
| `src/letmegetin/infrastructure/persistence/models.py` — new `LicenceModel`, `LicenceDestinationModel`, `PlaceAccessibilityWriteModel` | model | CRUD | `PlaceReviewDecisionModel` (256) / `ContributionModel` (99) | role-match |
| `migrations/versions/0011_licence_provenance.py` | migration | batch/backfill | `0010_duplicate_review.py` / `0009_place_source_category.py` | exact |
| `src/letmegetin/domain/places/entities.py` — extend `Place`, `PlaceAccessibility` | model (domain) | transform | `Place` / `PlaceAccessibility` (30, 59) | exact |
| `src/letmegetin/domain/places/licence.py` — `can_redistribute(licence, destination)` | domain pure | transform | `domain/places/dedup.py` (`classify_match`, 104) | exact |
| `src/letmegetin/domain/places/repositories.py` — `PlaceRepository` Protocol, new `LicenceRepository` | repository port | CRUD | `PlaceRepository` (23) / `CategoryMappingRepository` (170) | exact |
| `src/letmegetin/infrastructure/persistence/repositories.py` — `upsert_accessibility` rewrite + licence lookups | repository impl | CRUD | `upsert_accessibility` (867) + `_load_category_mapping` (seed 98) | exact |
| `src/letmegetin/infrastructure/persistence/mappers.py` — map provenance fields | mapper | transform | `place_from_model` (69), `place_accessibility_from_models` (93) | exact |
| `src/letmegetin/application/places/contribute.py` — pass source/actor/licence | use case | CRUD | `contribute` (18) | exact |
| `src/letmegetin/application/places/import_acceslibre.py` — pass source/licence | use case | batch | `_write_source_data` (197) / `_import_row` (203) | exact |
| `src/letmegetin/domain/places/acceslibre_map.py` — `accessibility_values` emits licence | transform | transform | `accessibility_values` (35) | exact |
| `src/letmegetin/application/referential/licences.py` — `sync`/`matrix`/`audit` use cases | service | batch/transform | `application/referential/families.py` (`load_families`, `apply_families`, `audit_families`) | exact |
| `src/letmegetin/admin.py` — new `licences` typer group | controller (CLI) | request-response | `families_app` (`sync`/`audit` at 347, 372) | exact |
| `src/letmegetin/api/schemas/places.py` — extend `PlaceDetailOut`, `AccessibilityValueOut` | schema | transform | `AccessibilityValueOut` (41), `PlaceDetailOut.from_detail` (145) | exact |
| `src/letmegetin/api/v1/places.py` — detail endpoint | controller | request-response | `place_detail` (139) | exact (schema-driven, likely no change) |
| `data/referential/licences.csv` | data | file-I/O | `data/referential/families.csv` | exact |
| `data/referential/licence_destinations.csv` | data | file-I/O | `data/referential/category_mapping.csv` | exact |
| `docs/public-api.md` | docs | n/a | (existing doc) | n/a |
| `tests/*` — unit/integration/functional | test | n/a | `tests/unit/application/referential/test_families.py`, `tests/functional/referential/test_admin_cli.py` | exact |

---

## Pattern Assignments

### 1. `PlaceModel` provenance columns (model, CRUD)

**Analog:** `PlacePhotoModel` (models.py 331-341) — the per-row `license` precedent named in CONTEXT.md.

```python
class PlacePhotoModel(Base):
    __tablename__ = "place_photo"
    __table_args__ = (UniqueConstraint("place_id", "url", name="place_photo_url_uc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    credit: Mapped[str | None] = mapped_column(String(255))
    license: Mapped[str | None] = mapped_column(String(64))
```

Copy the nullable `license: Mapped[str | None] = mapped_column(String(64))` shape onto `PlaceModel`:
`source_license: Mapped[str | None] = mapped_column(String(64))`, `source_url: Mapped[str | None] = mapped_column(String(1000))`, `retrieved_at: Mapped[datetime | None] = mapped_column()`, `observed_at: Mapped[datetime | None] = mapped_column()` (the source's claimed last-update — Acceslibre `date_maj`; D-16 exposes it, `retrieved_at` stays internal). Note `source` already exists (`String(32)`, line 224).

### 2. `PlaceAccessibilityModel` provenance columns (model, CRUD)

**Analog:** `PlaceMergeLogModel` (models.py 284-294) — the `actor` + `created` audit-column shape.

```python
class PlaceMergeLogModel(Base):
    __tablename__ = "place_merge_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    kept_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    merged_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Double)
    actor: Mapped[str] = mapped_column(String(32), server_default="importer")
    created: Mapped[datetime] = mapped_column(server_default=func.now())
```

Apply to `PlaceAccessibilityModel` (models.py 297-308): add
`source: Mapped[str] = mapped_column(String(32))`, `source_license: Mapped[str | None] = mapped_column(String(64))`, `observed_at: Mapped[datetime | None] = mapped_column()`, `recorded_at: Mapped[datetime] = mapped_column(server_default=func.now())`, `actor: Mapped[str] = mapped_column(String(64))`. `value` stays JSONB (D-01).

### 3. New write journal + licence tables (model, CRUD)

**Analog:** `ContributionModel` (models.py 99-109) for the append-only journal; `PlaceReviewDecisionModel` (256-271) for the decision/enum + CheckConstraint shape.

```python
class ContributionModel(Base):
    """Append-only audit log of an authenticated accessibility write (CONTRIB-02)."""
    __tablename__ = "contribution"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("criteria.id", ondelete="CASCADE"))
    value: Mapped[dict] = mapped_column(JSONB, default=dict)
    created: Mapped[datetime] = mapped_column(server_default=func.now())
```

```python
class PlaceReviewDecisionModel(Base):
    __tablename__ = "place_review_decision"
    __table_args__ = (
        CheckConstraint("decision IN ('merge','reject')", name="place_review_decision_decision_ck"),
    )
    ...
    decision: Mapped[str] = mapped_column(String(16))
    actor: Mapped[str] = mapped_column(String(32), server_default="operator")
    note: Mapped[str | None] = mapped_column(String(500))
    created: Mapped[datetime] = mapped_column(server_default=func.now())
```

`PlaceAccessibilityWriteModel` (D-12) mirrors `ContributionModel`: `place_id`, `criterion_id`, `value` (JSONB incoming value), `source`, `source_license`, `decision` (`CheckConstraint("decision IN ('accepted','rejected')")`), `reason` (NULLABLE, `CheckConstraint("reason IS NULL OR reason IN ('stale','other_source','not_redistributable')")` — an accepted write stores NULL), `actor`, `created`. `LicenceModel` (`licence` table, D-05): `slug` (unique/indexed), `name`, `url`, `obligations` (JSONB). `LicenceDestinationModel` (`licence_destination`, D-06): `licence_slug` (FK → `licence.slug`), `destination` (`CheckConstraint("destination IN ('open_export','osm','lov2_partner')")`), `allowed` (Boolean), `note`.

### 4. Alembic migration (migration, batch/backfill)

**Analog:** `0010_duplicate_review.py` (add columns + create table + FK + index + downgrade) and `0009_place_source_category.py` (simple `op.add_column` + index). Migration files use numeric revision strings, not hashes.

```python
revision: str = "0010"
down_revision: str | None = "0009"
# ...
def upgrade() -> None:
    op.add_column("place", sa.Column("duplicate_of_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "place_duplicate_of_id_fkey", "place", "place",
        ["duplicate_of_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_place_duplicate_of_id", "place", ["duplicate_of_id"], unique=False)
    op.create_table(
        "place_review_decision",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # ... columns, ForeignKeyConstraint, CheckConstraint, PrimaryKeyConstraint
    )
    op.create_index("ix_place_review_decision_place_id", "place_review_decision", ["place_id"], unique=False)

def downgrade() -> None:
    op.drop_index(...); op.drop_table(...); op.drop_constraint(...); op.drop_column(...)
```

The `0011` migration adds: `place` columns (incl. nullable `place.observed_at`), `place_accessibility` columns, the three new tables, **and the D-04 backfill**. For the data backfill use `op.execute(...)` (see the seed's raw-SQL `text(...)` style in `test_admin_cli.py` 205-215 for the `CAST(:label AS jsonb)` idiom). Backfill resolves the source → licence mapping from `data/referential/source_licences.csv` (stdlib `csv`), never a hard-coded `CASE` (LIC-05); answer `source`/`source_license` from `value->>'source'`, `recorded_at = now()`, `observed_at`/`retrieved_at` stay NULL. The model must register the new tables for `alembic` autogenerate — they live in `models.py`, imported by `migrations/env.py` line 17.

### 5. Domain entities provenance fields (domain model, transform)

**Analog:** `Place` (entities.py 30-56) and `PlaceAccessibility` (59-66). Add `source_license`, `source_url`, `retrieved_at`, `observed_at` to `Place`; `source`, `source_license`, `observed_at`, `recorded_at`, `actor` to `PlaceAccessibility`. These are plain dataclass fields with `None` defaults, matching the existing `source_id: str | None = None` style.

### 6. `can_redistribute` pure predicate (domain pure, transform)

**Analog:** `domain/places/dedup.py` — a stdlib-only pure module with named constants and one predicate (`classify_match`, lines 104-110).

```python
def classify_match(score: float) -> MatchKind:
    """Bucket a similarity score: auto link, review queue, or distinct place."""
    if score >= AUTO_MATCH_THRESHOLD:
        return "auto"
    if score >= REVIEW_MATCH_THRESHOLD:
        return "review"
    return "new"
```

`domain/places/licence.py` exposes `can_redistribute(licence: str | None, destination: str, matrix: Mapping[...] | None = None) -> bool`. D-13/D-15: fail-closed — return `False` for `None` or an unknown licence; otherwise look up the `(licence, destination)` row. Keep it a pure function taking the matrix in (no DB), so `domain/` stays clean and the SQL `JOIN licence_destination` in the repository is the pushed-down twin. LIC-03 is a **row** (`osm × lov2_partner = false`), not a branch.

### 7. Repository port additions (repository port, CRUD)

**Analog:** `PlaceRepository` (repositories.py 23) and `CategoryMappingRepository` (170-173) — `Protocol` classes with `...` bodies.

`upsert_accessibility` signature must change to carry provenance. Today it is `async def upsert_accessibility(self, place_id: int, values: dict[str, dict[str, object]]) -> None` (line 110-114). The rewrite (D-09/D-10/D-11/D-12) needs source/actor/licence/observed_at per write, so the port and both callers change together. Add a `LicenceRepository` Protocol with `get_by_slug(slug) -> Licence | None` and `list_destinations(licence_slug) -> list[LicenceDestination]` / `allowed(licence_slug, destination) -> bool`.

### 8. `upsert_accessibility` rewrite + licence lookups (repository impl, CRUD)

**Analog:** the current `upsert_accessibility` (repositories.py 867-894) for the bulk `insert(...).on_conflict_do_update` idiom, and seed's `_load_category_mapping` (seed.py 98-129) for the CSV→table `insert(...).on_conflict_do_update(constraint=...)` idiom the new licence sync reuses.

```python
async def upsert_accessibility(self, place_id: int, values: dict[str, dict[str, object]]) -> None:
    if not values:
        return
    slugs = list(values)
    rows = (await self._session.execute(
        select(CriterionModel.id, CriterionModel.slug).where(CriterionModel.slug.in_(slugs))
    )).all()
    if not rows:
        return
    statement = insert(PlaceAccessibilityModel).values(
        [
            {"place_id": place_id, "criterion_id": criterion_id, "value": values[slug]}
            for criterion_id, slug in rows
        ]
    )
    await self._session.execute(
        statement.on_conflict_do_update(
            index_elements=[PlaceAccessibilityModel.place_id, PlaceAccessibilityModel.criterion_id],
            set_={"value": statement.excluded.value},
        )
    )
```

```python
statement = insert(CategoryMappingModel).values(**values)
await session.execute(
    statement.on_conflict_do_update(
        constraint="category_mapping_category_uc",
        set_={key: value for key, value in values.items() if key != "category_id"},
    )
)
```

The rewrite must: (a) resolve the current row's `source`/`observed_at` before the write; (b) reject when the row belongs to another source (D-09, `reason='other_source'`) or the incoming `observed_at` is older (D-10, `reason='stale'`), allowing inserts on absent criteria owned by another source (D-11); (c) append a `PlaceAccessibilityWriteModel` row on every attempt with `decision`/`reason` (D-12); (d) stamp `source`, `source_license`, `observed_at`, `recorded_at`, `actor` on the winning row. Both callers (`contribute.py` 34 and `import_acceslibre.py` 199) must pass provenance explicitly.

### 9. Mappers (mapper, transform)

**Analog:** `place_from_model` (mappers.py 69-90) and `place_accessibility_from_models` (93-101). Add the new provenance fields to the returned entities, exactly as `source=model.source` is copied today. `place_accessibility_from_models` currently returns only `criterion_slug`, `label`, `handicap_families`, `value` — extend it to also copy `source`, `source_license`, `observed_at` so `get_place` → schema can surface them (D-16).

### 10. `contribute` use case (use case, CRUD)

**Analog:** `contribute` (contribute.py 18-35). The stored dict today is `{"value": value, "source": "user", "user_id": user.id}`. Per D-03/D-09 it becomes `{"value": value, "source": "user", "actor": f"user:{user.id}", ...}` with a licence resolved by the repository, and the `upsert_accessibility` call passes `source='user'`, `actor=f'user:{user.id}'` explicitly. `add_contribution` (line 35) stays as-is.

### 11. AccesLibre import use case (use case, batch)

**Analog:** `_write_source_data` (import_acceslibre.py 197-200) and `_import_row` (203-269). `SOURCE_ACCESLIBRE = "acceslibre"` (line 32) already exists; pass `source=SOURCE_ACCESLIBRE`, `actor=f"importer:{SOURCE_ACCESLIBRE}"` and `observed_at=row.observed_at` (from the export's `date_maj`, mapped via `_COLUMNS["observed_at"] = ("date_maj", "date_mise_a_jour", "updated_at")`) through `_write_source_data` → `upsert_accessibility`. The licence is resolved by the repository from `source_licence` — NO `SOURCE_LICENCE_ACCESLIBRE` constant (LIC-05). `accessibility_values` (line 144) stays `{"value", "source", "key"}` — provenance lives in columns, not the JSONB (D-01).

### 12. `acceslibre_map.accessibility_values` (transform, transform)

**Analog:** `accessibility_values` (acceslibre_map.py 35-43). It stays UNCHANGED — it emits `{"value": raw, "source": SOURCE, "key": key}` and the licence is resolved by the repository from `source_licence` at write time, never added to the JSONB `value` (D-01). `SOURCE = "acceslibre"` (line 13) is the constant to reuse.

### 13. Licence admin use cases (service, batch/transform)

**Analog:** `application/referential/families.py` — the exact reviewed-CSV shape D-05/D-08 must reproduce. Three functions to mirror:

```python
def load_families(path: Path) -> dict[str, list[str]]:
    """Read ``slug;families`` rows where families are ``|``-separated."""
    assignments: dict[str, list[str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            slug = (row.get("slug") or "").strip()
            if not slug:
                continue
            if slug in assignments:
                raise DomainError(f"duplicate families row for '{slug}'")
            families = [name.strip() for name in (row.get("families") or "").split("|")]
            if not any(families):
                raise DomainError(f"families row '{slug}' names no handicap family")
            assignments[slug] = _validated(slug, [name for name in families if name])
    return assignments
```

```python
async def apply_families(criteria, filters, assignments, *, overwrite=False) -> FamiliesReport:
    """Write explicit rows, then let options inherit and groups union their children."""
    # report counters + upsert loop
```

```python
async def audit_families(criteria, filters) -> list[str]:
    """Return the slugs that carry no facility family, criteria first then filters."""
    missing_criteria = sorted(item.slug for item in await criteria.list_all() if not item.handicap_families)
    missing_filters = sorted(item.slug for item in await filters.list_all() if not item.handicap_families)
    return missing_criteria + missing_filters
```

`licences.py` mirrors this trio: `load_licences(path)` and `load_licence_destinations(path)` (CSV readers returning domain objects, raising `DomainError` on dup/unknown/empty), `sync_licences(licence_repo, destination_repo, licences, destinations) -> LicenceReport` (upsert; report `created`/`skipped`), `audit_licences(...) -> list[str]` (return slugs with no matrix rule / unknown licence; caller exits 1). The `matrix` command is a read-only render of `licence_destination` grouped by destination.

### 14. Admin CLI `licences` group (controller/CLI, request-response)

**Analog:** `families_app` (`admin.py` 96, `sync` at 347-369, `audit` at 372-389) and the `_run_admin` runner (117-145).

```python
families_app = typer.Typer(help="Fill and audit handicap families (moteur, auditif, visuel…).")
# ...
app.add_typer(families_app, name="families")
```

```python
@families_app.command("sync")
def families_sync(
    file: Annotated[Path | None, typer.Option("--file", "-f", help="Reviewed families CSV")] = None,
    force: Annotated[bool, typer.Option("--force", ...)] = False,
) -> None:
    path = file or settings.data_dir / "families.csv"
    async def callback(session: AsyncSession) -> str:
        report = await apply_families(
            SqlAlchemyCriterionRepository(session),
            SqlAlchemyFilterRepository(session),
            load_families(path), overwrite=force,
        )
        return f"families sync: criteria={report.criteria_updated} ..."
    _run_admin(callback)
```

```python
@families_app.command("audit")
def families_audit() -> None:
    async def missing() -> list[str]:
        async with SessionLocal() as session:
            return await audit_families(...)
    slugs = asyncio.run(missing())
    if not slugs:
        typer.echo("families ok: ..."); return
    for slug in slugs:
        typer.echo(slug)
    raise typer.Exit(code=1)
```

Add `licences_app = typer.Typer(...)` with `sync` (loads both CSVs, `_run_admin(callback)` — the default `bump=True` bumps `referential_version`, satisfying D-08), `matrix` (`_run_admin(callback, bump=False)`), `audit` (exit-1 pattern above). Register with `app.add_typer(licences_app, name="licences")`.

### 15. API schema additions (schema, transform)

**Analog:** `AccessibilityValueOut` (schemas/places.py 41-47) and `PlaceDetailOut.from_detail` (145-168).

```python
class AccessibilityValueOut(BaseModel):
    criterion: str
    label: dict[str, str]
    handicap_families: list[str]
    value: dict[str, Any]
```

Add `source: str | None = None`, `license: str | None = None`, `observed_at: datetime | None = None` to `AccessibilityValueOut`, and `source`, `license`, `observed_at` to `PlaceDetailOut` (or extend `PlaceSummaryOut` — D-16 says "on the place and on every answer, as optional additive fields"). Populate in `from_detail` (lines 146-168) from `detail.place` / `value`. `Place` already exposes `source`; add `source_license`/`retrieved_at` passthrough. The field name is `license` in the schema (D-16 "exposes `source`, `license`"), mapped from the model's `source_license`.

### 16. Detail endpoint (controller, request-response)

**Analog:** `place_detail` (places.py 139-148). No signature change needed — it is `response_model=PlaceDetailOut`, schema-driven. Provenance flows through `get_place` → `PlaceDetail` → `PlaceDetailOut.from_detail`. `get_place.py` (get_place 35-68) needs no logic change beyond the mapper surfacing the fields; the `PlaceDetail` dataclass already carries `place` and `accessibility` lists.

### 17/18. Reviewed data CSVs (data, file-I/O)

**Analog:** `data/referential/families.csv` (`slug;families`, delimiter `;`) and `category_mapping.csv` (`slug;name;...;notes`). `licences.csv` → `slug;name;url;obligations` (obligations `|`-separated like `families`), `licence_destinations.csv` → `licence_slug;destination;allowed;note`. Same `;` delimiter, UTF-8, header row, blank-line-skipped. Loaded by `seed.py` (D-05: seed order — licences before the import resolves them, per CONTEXT "Integration Points").

### 19. Seed integration (seed.py)

**Analog:** `seed()` (seed.py 132-242) — call `load_licences`/`sync_licences` alongside the existing `apply_families` (line 223) and `_load_category_mapping` (line 221) before `rebuild_category_grids` (229).

---

## Shared Patterns

### Domain-pure predicate ↔ SQL twin (D-13)
- **Reference:** `domain/places/licence.py` `can_redistribute(...)` — the only place the rule lives.
- **SQL twin:** in `SqlAlchemyLicenceRepository` (or the place repo), a `JOIN licence_destination ON licence_destination.licence_slug = place.source_license AND licence_destination.destination = :dest AND licence_destination.allowed` for bulk extraction (D-14: exclude + count, never fail). Mirror `SqlAlchemyCoverageRepository.by_category_country` (repositories.py 1064-1091) for the `select(...).group_by(...)` counter shape.

### Error handling (domain errors → CLI exit 1, HTTP 404)
- **Source:** `admin.py` `_run_admin` (117-145) — `except DomainError as exc: typer.echo(str(exc), err=True); raise typer.Exit(code=1) from exc`.
- **Source:** `places.py` detail endpoint (144-147) — `except PlaceNotFound: raise HTTPException(404, ...) from None`.
- **Apply to:** licence sync/audit (CLI), all new repository methods raise `DomainError` from `core.exceptions` (see `repositories.py` line 14 import, used at 108/195/685).

### CSV loading + validation
- **Source:** `families.py` `load_families` (38-52) and `_validated` (28-35) — `csv.DictReader(handle, delimiter=";")`, duplicate-slug and unknown-value rejection via `DomainError`.
- **Apply to:** `licences.py` loaders.

### Referential version bump on licence-data change (D-08)
- **Source:** `admin.py` `_run_admin` default `bump=True` → `rebuild_category_grids` → `SqlAlchemyCategoryGridRepository.bump_version` (repositories.py 1154-1161).
- **Apply to:** `licences sync` (leave default `bump=True`); `matrix`/`audit` use `bump=False`.

### Append-only journal convention (D-12)
- **Source:** `ContributionModel` docstring "Append-only audit log" (models.py 100); `add_contribution` (repositories.py 965-986) — never update, always append.
- **Apply to:** `PlaceAccessibilityWriteModel` writes.

### Test layout
- **Unit (pure):** `tests/unit/application/referential/test_families.py` — `FakeCriterionRepository`/`FakeFilterRepository` in-file fakes (lines 18-46), CSV written to `tmp_path` (83-87), `pytest.raises(DomainError, match=...)` (104-105). Mirror for `load_licences`, `sync_licences`, `audit_licences`, and `can_redistribute` (pure predicate: table-driven `pytest.mark.parametrize`).
- **Functional (real DB):** `tests/functional/referential/test_admin_cli.py` — `CliRunner().invoke(admin.app, ["families", "sync"])`, assert `exit_code == 0` / `== 1`, raw-SQL seed via `text(...)` (203-216). Mirror for `licences sync|matrix|audit`, and add `tests/functional/places/test_places_import.py` coverage for the conflict/freshness rules (D-09/D-10/D-11/D-12) via `require_database("place_accessibility")`.
- **Integration:** `tests/integration/api/test_api.py` — assert the detail response now carries `source`/`license`/`observed_at` (D-16); `tests/integration/api/test_openapi.py` catches the regenerated schema.
- **Fakes for use-case tests:** `tests/unit/application/referential/fakes.py` — shared repository fakes used across referential admin tests; extend with a `FakeLicenceRepository`.

---

## No Analog Found

None — every file has a close, git-tracked in-repo analog (the families/CSV/category-mapping lineage and the existing `upsert_accessibility` write path are exact precedents).

## Metadata

**Analog search scope:** `src/letmegetin/{domain,application,infrastructure,api}/`, `migrations/versions/`, `data/referential/`, `tests/`, `docs/`
**Files scanned:** 24
**Pattern extraction date:** 2026-11-13
**Tracked-source gate:** all named analogs live under `src/`, `migrations/`, `data/`, `tests/`, `docs/` (repo source tree; no `.gsd/capabilities` mirrors involved).
