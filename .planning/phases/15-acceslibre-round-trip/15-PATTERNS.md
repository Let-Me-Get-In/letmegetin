# Phase 15: AccesLibre round trip - Pattern Map

**Mapped:** 2026-11-15
**Files analyzed:** 19 (new + modified)
**Analogs found:** 17 / 19 (2 have no in-repo analog: the httpx adapter and its integration test)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `application/places/export.py` (modify: parameterise `DESTINATION`) | service / use case | streaming + file-I/O | itself (`export.py:61,258,279,288-290,341`) | exact (self-edit) |
| `domain/places/acceslibre_map.py` (modify: inverse `FIELD_MAP`) | utility (pure map) | transform | itself (`:21-43`) | exact (self-edit) |
| `domain/places/acceslibre_push.py` (new: diff/freshness/payload typing) | domain (pure) | transform | `domain/places/acceslibre_map.py`, `domain/places/export.py:66-72` | role-match |
| `domain/places/lov2_projection.py` (new: key/category/criterion projection) | domain (pure) | transform | `domain/places/acceslibre_map.py`, `domain/places/export_plan.py` | role-match |
| `application/places/push_acceslibre.py` (new use case) | application use case | request-response + journal | `application/places/import_acceslibre.py`, `contribute.py` | role-match |
| `application/places/lov2_export.py` (new: parameterised export entry) | application use case | streaming + file-I/O | `application/places/export.py` | exact |
| `infrastructure/acceslibre/client.py` (new httpx adapter) | infrastructure adapter | request-response (HTTP) | **none** — RESEARCH `MockTransport` + `config.py` settings | no analog |
| `infrastructure/persistence/push_repositories.py` (new: owned-row stream + journal) | infrastructure repository | CRUD + streaming | `infrastructure/persistence/export_repositories.py`, `repositories.py:842-858,1058-1160` | role-match |
| `infrastructure/persistence/models.py` (modify: new journal model) | model | CRUD | `PlaceAccessibilityWriteModel` (`models.py:326-350`) | exact |
| `admin.py` (modify: `acceslibre push` command) | operator CLI | request-response | `export_app` / `import_app` (`admin.py:115-132,905-948,415-446`) | exact |
| `config.py` (modify: API key + base URL) | config | config | itself (`config.py:13-43`) | exact (self-edit) |
| `migrations/versions/0014_*.py` (new journal table) | migration | batch | `0013_licence_attribution_text.py` | exact |
| `migrations/versions/0015_*.py` (dual licence re-stamp, may merge into 0014) | migration (data) | batch | `0013` + `tests/db.py:77-101` seed pattern | exact |
| `data/referential/acceslibre_mapping.csv` (new) | data | file-I/O | `data/referential/licence_destinations.csv` (versioned CSV + loader) | role-match |
| `data/referential/licences.csv` / `licence_destinations.csv` / `source_licences.csv` (modify: `dual`) | data | file-I/O | themselves (sync via `admin licences sync`, `admin.py:415-446`) | exact |
| `docs/` partner prose (new) | docs | — | `docs/public-api.md` §ODbL export | partial |
| `tests/unit/domain/places/test_acceslibre_push.py`, `test_lov2_projection.py` (new) | test (unit) | — | `domain` pure tests | role-match |
| `tests/integration/acceslibre/test_client.py` + `fakes.py` (new) | test (integration) | — | **none** (no HTTP client test exists); RESEARCH stub + `tests/integration/referential/test_seed_vocabulary.py` | no analog |
| `tests/functional/places/test_acceslibre_push.py`, `test_lov2_export.py` (new) | test (functional) | — | `tests/functional/places/test_export.py`, `tests/db.py`, `tests/functional/conftest.py` | exact |

---

## Pattern Assignments

### 1. `application/places/export.py` — parameterise the destination (service, streaming + file-I/O)

**Analog:** itself. The constant is read in exactly four places and threaded nowhere. Change = add a `destination: str` parameter and stop reading the constant.

**Constant to remove** (`export.py:61`):
```python
DESTINATION = "open_export"
```

**Read sites to thread** (`_write_zip`, `export.py:237-246` signature, then `:258, :279, :288-290`):
```python
async def _write_zip(
    archive_path: Path,
    export: ExportPlanRepository,
    *,
    generated_at: datetime,
    mode: str,
    boundary: int,
    from_seq: int | None,
    answer_window: tuple[int, int] | None,
) -> _ZipResult:
```
Inside it the three exclusion/stream calls hard-code `DESTINATION`:
```python
_seeing(export.stream_canonical_places(DESTINATION, from_seq), presence)   # :258
_seeing(export.stream_answers(DESTINATION, answer_window), presence)        # :279
excluded_places = await export.place_exclusion_counts(DESTINATION)          # :288
excluded_answers = await export.answer_exclusion_counts(DESTINATION)        # :289
withheld_answers = await export.place_withheld_answer_counts(DESTINATION)   # :290
```

**Use-case signature** (`export_odbl`, `export.py:341-349`) already takes `out: Path`; add `destination: str = "open_export"` beside it:
```python
async def export_odbl(
    export: ExportPlanRepository,
    events: ExportEventRepository,
    *,
    out: Path,
    since: int | None = None,
    since_date: date | None = None,
    delta: bool = False,
) -> ExportReport:
```

**Archive-name / output separation (Pitfall 1):** the partner archive and its `latest.json` must go to a directory **outside** `settings.export_dir` (`config.py:20`). The `--out` flag already exists on the CLI (`admin.py:907`); the planner threads it and adds a functional test that `GET /api/v1/export/<partner>.zip` returns 404. The served route reads `settings.export_dir` only (`api/v1/export.py:34,41,54`) — no route change.

---

### 2. `domain/places/acceslibre_map.py` — inverse `FIELD_MAP` (utility, transform)

**Analog:** itself (`acceslibre_map.py:21-43`). Add the inverse beside the map; no new data file (D-07, bijective — verified 8 distinct slugs).

```python
FIELD_MAP: dict[str, str] = {          # :21-30 — keys = their field, values = our slug
    "entree_pmr": "entree-acces",
    "entree_largeur_mini": "entree-largeur-de-porte-cm",
    "entree_marches": "entree-obstacles-a-la-porte-d-entree",
    "entree_porte_manoeuvre": "entree-ouverture-de-porte",
    "accueil_cheminement_plain_pied": "circulation-circulation-dans-les-allees",
    "sanitaires_presence": "services-et-equipements-sanitaires",
    "stationnement_ext_pmr": "exterieur-place-gig-gic-a-proximite",
    "transport_station_presence": "exterieur-transports-accessibles-a-proximite",
}
```
Add: `THEIR_FIELD_FOR_SLUG = {slug: field for field, slug in FIELD_MAP.items()}` (the reverse dict). Keep the module header comment pattern (`:1-6`), `from __future__ import annotations` (`:8`), `from collections.abc import Mapping` (`:10`).

---

### 3. `domain/places/acceslibre_push.py` — pure diff + freshness decision + payload typing (domain, transform)

**Analog:** `domain/places/acceslibre_map.py` (pure module, dict maps, `Mapping` input) and `domain/places/export.py:66-72` (`describe_changes`, the existing pure diff).

**Header + imports pattern** (from `acceslibre_map.py:1-11`, `export.py:1-14`):
```python
"""Pure push decision: read-then-diff, freshness, outbound payload typing (D-10/D-11)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal
```

**Existing diff to mirror** (`domain/places/export.py:66-72`) — but the push needs *typed* comparison (Pitfall 9), so normalise both sides before this:
```python
def describe_changes(before: dict[str, object], after: dict[str, object]) -> dict[str, object]:
    return {
        key: after.get(key)
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }
```

**Freshness rule (Pitfall 5) — named decision, not a `_rejection` reuse:** our claim date for a `user` answer is `recorded_at` (never NULL `observed_at`; `contribute.py:39` writes `observed_at=None`). Their side exposes only ERP-level `updated_at`. State the rule as a pure function; the planner names it. Do **not** import `repositories._rejection` (`repositories.py:392-411`) — extract that logic into a domain function both paths call (research "Don't Hand-Roll").

**Payload typing (Pitfall 7 + 10):** validate each outbound value against the schema type (booleans only `{true,false}`, integers in range, enum membership) and emit `value["value"]` only — never `user_id` (`contribute.py:33` stores `{"value": …, "source": "user", "user_id": user.id}`).

---

### 4. `domain/places/lov2_projection.py` — our keys → partner keys (domain, transform)

**Analog:** `domain/places/acceslibre_map.py` (pure map) + `domain/places/export_plan.py` (frozen dataclass rows with `to_csv`, `:99-144`).

**Dataclass pattern** (`export_plan.py:99-123`, `frozen=True, slots=True`):
```python
@dataclass(frozen=True, slots=True)
class PlaceRow:
    place_id: int
    origin_id: str | None
    slug: str
    ...
    def to_csv(self) -> tuple[object, ...]:
        return (...)
```

**Fail-closed on unmappable rows** (D-05/D-06/D-08): a place with no ERP identifier, or a category/criterion with no inverse row, becomes a mapping-document row — never a silent skip. Use `DomainError` (`core/exceptions.py:6-7`) exactly as `_read_latest` does (`export.py:116`):
```python
raise DomainError(f"{path} is unreadable: {exc}") from exc
```

**Canonical category inverse (Pitfall 4):** `acceslibre_categories.csv` is 391 rows over 133 `category_slug` (not a bijection). Projection takes the inverse map as an **input** and picks the canonical `activite` (max `places`). Column order: `activite;category_slug;places`.

---

### 5. `application/places/push_acceslibre.py` — push use case (application, request-response + journal)

**Analog:** `application/places/import_acceslibre.py` (use case + report dataclass, `:52-82`; orchestration loop `:303-343`) and `contribute.py` (thin orchestration over `PlaceRepository`).

**Report dataclass pattern** (`import_acceslibre.py:72-81`):
```python
@dataclass
class ImportReport:
    created: int = 0
    linked: int = 0
    review: int = 0
    skipped: int = 0
    resolved: int = 0
    unresolved: dict[str, int] = field(default_factory=dict)
```

**Use-case function shape** (`import_acceslibre.py:303-314`): takes repository ports, an iterable, and keyword flags; returns the report. The push mirrors it with the AccesLibre client port + the push repository port:
```python
async def import_acceslibre(
    places: PlaceRepository,
    categories: CategoryRepository,
    mapping: CategoryMappingRepository,
    place_aliases: PlaceAliasRepository,
    merges: MergeLogRepository,
    rows: Iterable[AcceslibreRow],
    *,
    aliases: Mapping[str, str] | None = None,
    dry_run: bool = False,
    dedup: bool = True,
) -> ImportReport:
```

The push reads owned rows (`source='user'`, licence allows `lov2_partner`), GETs each, diffs (domain fn), PATCHes only what differs, journals every decision. `--dry-run` = print diff, write nothing (`import_acceslibre.py` already models `dry_run` at `:291-292`).

---

### 6. `infrastructure/acceslibre/client.py` — httpx adapter (infrastructure, HTTP request-response)

**No in-repo analog** (httpx is dev-only today; no runtime HTTP adapter exists). Use the RESEARCH stub shape and `config.py` settings pattern.

**Settings to add** (`config.py:13-21` pattern; `env_prefix="LETMEGETIN_"`):
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LETMEGETIN_", extra="ignore")
    ...
    acceslibre_api_key: str | None = None
    acceslibre_base_url: str = "https://acceslibre.beta.gouv.fr"
```

**Adapter contract (from RESEARCH §Code Examples + Security V9):** fixed origin (a constant, never a setting), `Authorization: Api-Key <key>`, `timeout=`, default `verify=True`, `follow_redirects=False`. Keep `httpx` out of `domain/` and `application/` — the port is a `Protocol` in the domain, like `ExportEventRepository` (`domain/places/export.py:33-63`) or `PlaceRepository` (`domain/places/repositories.py:24-140`).

**Port pattern to copy** (`domain/places/export.py:33-36`):
```python
class ExportEventRepository(Protocol):
    async def append(self, entity: ExportEntity, entity_id: int, op: ExportOp, actor: str, payload: dict[str, object]) -> None: ...
```

**Retry (Don't Hand-Roll):** bounded explicit loop on 429/5xx honouring `Retry-After` when present; no backoff library. httpx transport `retries=` does not cover HTTP status codes.

**Key redaction (V7/V8):** the adapter never logs the `Authorization` header; exception messages carry slug + status only.

---

### 7. `infrastructure/persistence/push_repositories.py` — owned-row stream + journal (infrastructure, CRUD + streaming)

**Analog:** `infrastructure/persistence/export_repositories.py` (licence-gated streaming, `_licence_allows` `:64-78`, `stream_answers` `:332-362`) and `repositories.py` (`_source_licence` `:842-858`, `upsert_accessibility` journal insert `:1098-1133`).

**Licence-gate SQL twin** (`export_repositories.py:64-78`) — reuse, never a third copy:
```python
def _licence_allows(licence: ColumnElement[str | None] | InstrumentedAttribute[str | None], destination: str) -> ColumnElement[bool]:
    return exists(
        select(1).where(
            LicenceDestinationModel.licence_slug == licence,
            LicenceDestinationModel.destination == destination,
            LicenceDestinationModel.allowed.is_(True),
        )
    )
```

**Journal insert pattern** (`repositories.py:1132-1133`, every attempt incl. losing value):
```python
await self._session.execute(insert(PlaceAccessibilityWriteModel).values(journal))
```
The push journal is a **new** append-only table (Pitfall 6: `place_accessibility_write` CHECKs `decision IN ('accepted','rejected')` and reasons `stale/other_source/not_redistributable` do not fit `skipped` / `their_fresher` / `rpa_locked`).

**Repository class shell** (`export_repositories.py:250-254`):
```python
class SqlAlchemyExportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
```

---

### 8. `infrastructure/persistence/models.py` — new journal model (model, CRUD)

**Analog:** `PlaceAccessibilityWriteModel` (`models.py:326-350`) — copy the append-only shape, new CHECKs.

```python
class PlaceAccessibilityWriteModel(Base):
    __tablename__ = "place_accessibility_write"
    __table_args__ = (
        CheckConstraint("decision IN ('accepted','rejected')", name="place_accessibility_write_decision_ck"),
        CheckConstraint(
            "reason IS NULL OR reason IN ('stale','other_source','not_redistributable')",
            name="place_accessibility_write_reason_ck",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("place.id", ondelete="CASCADE"), index=True)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("criteria.id", ondelete="CASCADE"))
    value: Mapped[dict] = mapped_column(JSONB, default=dict)
    source: Mapped[str] = mapped_column(String(32))
    source_license: Mapped[str | None] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(64))
    created: Mapped[datetime] = mapped_column(server_default=func.now())
```
The new `acceslibre_push_write` model uses the same `Mapped[...]` / `mapped_column` / `JSONB` / `CheckConstraint` vocabulary with `decision IN ('accepted','skipped')` and its own reason set.

---

### 9. `admin.py` — `acceslibre push` command (operator CLI, request-response)

**Analog:** the Typer sub-command pattern. Register a new group beside `import_app`/`export_app` (`admin.py:115-132`), then a command mirroring `export_odbl_command` (`:905-948`).

**Group registration** (`admin.py:115,118,128,130`):
```python
import_app = typer.Typer(help="Import open place datasets (Acceslibre first).")
export_app = typer.Typer(help="Write the open ODbL export (snapshot, delta or catch-up).")
app.add_typer(import_app, name="import")
app.add_typer(export_app, name="export")
```

**Command + `_run_admin` callback** (`admin.py:905-948`, the exact shape `--dry-run` plugs into — `_run_admin(..., commit=False)` rolls back, `admin.py:140-168`):
```python
@export_app.command("odbl")
def export_odbl_command(
    out: Annotated[Path, typer.Option("--out", help="Directory the ZIPs and latest.json go to")],
    delta: Annotated[bool, typer.Option("--delta", help="...")] = False,
    since: Annotated[str | None, typer.Option("--since", help="...")] = None,
) -> None:
    async def callback(session: AsyncSession) -> str:
        report = await export_odbl(
            SqlAlchemyExportRepository(session),
            SqlAlchemyExportEventRepository(session),
            out=out, since=since_seq, since_date=since_date, delta=delta,
        )
        return "\n".join(lines)
    _run_admin(callback, bump=False)
```
The new `@acceslibre_app.command("push")` takes `--dry-run`, builds the httpx adapter + push repository, and calls the push use case. `_run_admin(callback, bump=False, commit=False)` for dry-run (rollback; `_run_admin` already supports `commit=False` at `:157-160`).

---

### 10. `migrations/versions/0014_*.py` (and `0015`) — journal table + `dual` re-stamp (migration, batch)

**Analog:** `migrations/versions/0013_licence_attribution_text.py:1-28` — the header block and `upgrade/downgrade` shape.

```python
"""new append-only acceslibre push journal

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "acceslibre_push_write",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("place.id", ondelete="CASCADE"), index=True),
        sa.Column("criterion_id", sa.Integer(), sa.ForeignKey("criteria.id", ondelete="CASCADE")),
        sa.Column("value", sa.dialects.postgresql.JSONB(), default=dict),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(32), nullable=True),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("created", sa.DateTime(), server_default=sa.func.now()),
        sa.CheckConstraint("decision IN ('accepted','skipped')", name="acceslibre_push_write_decision_ck"),
        sa.CheckConstraint(
            "reason IS NULL OR reason IN ('their_fresher','rpa_locked','not_redistributable','unmappable')",
            name="acceslibre_push_write_reason_ck",
        ),
    )


def downgrade() -> None:
    op.drop_table("acceslibre_push_write")
```

The `dual` re-stamp migration (Pitfall 3, `0015` or merged) updates `place_accessibility.source_license` from `odbl` to `dual` where `source='user'` — a data migration, gated on a `checkpoint:human-verify` (contributor-terms decision). Note: `source_licence` has `source` as PK (`models.py:424`), and rows are stamped at write time (`repositories.py:1114,1127`), so the CSV edit alone does **not** re-stamp existing rows.

---

### 11. `data/referential/acceslibre_mapping.csv` + licence CSV edits (data, file-I/O)

**Analog:** the reviewed-CSV + loader + `admin … sync` + audit pattern (`licences.csv` / `families.csv`; `admin.py:415-446` `licences_sync`; `licence_repositories.py:39-40` `SqlAlchemyLicenceRepository`).

**`dual` rows to add** (verbatim column order from RESEARCH §Sources):
- `licences.csv` header `slug;name;url;obligations;attribution_text` → add `dual` with reviewed `attribution_text` naming both licences (D-02).
- `licence_destinations.csv` header `licence_slug;destination;allowed;note` → add `dual;lov2_partner;true;…` and `dual;open_export;true;…` and `dual;osm;true;…` (D-01).
- `source_licences.csv` header `source;licence_slug;effective_from` → change `user;odbl;2026-10-26` to `user;dual;…` (D-01).

**Mapping CSV loader (D-09):** follows `load_licences` / `load_licence_destinations` / `load_source_licences` in `application/referential/licences.py`, loaded by the projection as an input, fail-closed on a gap (`DomainError`, D-08 "never silently omit"). Column shape is the agent's discretion but each row must name the entity, the reason and the identifier (D-05/D-06/D-08).

---

### 12. Tests

**Unit (domain)** — `tests/unit/domain/places/test_acceslibre_push.py`, `test_lov2_projection.py`: pure functions, no DB/network (testing.md kind `unit`). Mirror `domain` pure tests; `pytest.mark` tag by folder is automatic (`tests/conftest.py`).

**Integration (stub HTTP)** — `tests/integration/acceslibre/test_client.py` + `fakes.py`: **no in-repo analog** for an HTTP client. Use the RESEARCH `httpx.MockTransport` stub (kind `integration`, boundary mocked):
```python
import httpx

def _stub(request: httpx.Request) -> httpx.Response:
    if request.method == "GET":
        return httpx.Response(200, json={"slug": "x", "accessibilite": {"entree": {"entree_pmr": None}}})
    return httpx.Response(200, json={"slug": "x"})

client = httpx.Client(transport=httpx.MockTransport(_stub), base_url="https://acceslibre.beta.gouv.fr")
```
Shared stub handler lives in one kit file `tests/integration/acceslibre/fakes.py`, never copied (testing.md:47). Fixture monkeypatches `settings.acceslibre_api_key` (new field), never reads a real key (testing.md:21).

**Functional** — `tests/functional/places/test_acceslibre_push.py`, `test_lov2_export.py`: copy `tests/functional/places/test_export.py` wholesale (CliRunner + real PostGIS). Fixtures from `tests/functional/conftest.py` (`reviewed_source_licences`, `test_sessions`, `db`) and helpers from `tests/db.py` (`require_database`, `execute`, `scalar`, `rows`, `seed_source_licences`).

**Functional test shell** (`test_export.py:52-70` — `db` fixture overrides to seed/clean its own rows):
```python
@pytest.fixture
def db(test_sessions: None) -> Iterator[None]:
    require_database("export_event", "place", "criteria", "categories", "licence", "licence_destination")
    _cleanup()
    _seed()
    yield
    _cleanup()
```

---

## Shared Patterns

### Licence gate (fail-closed) — apply to feed AND push
**Source:** `domain/places/licence.py:18-30` (predicate) + `infrastructure/persistence/export_repositories.py:64-78` (SQL twin). `DESTINATIONS` already includes `"lov2_partner"` (`licence.py:15`). Call the existing pair — never write a third copy.

### Error handling (fail-closed)
**Source:** `core/exceptions.py:6-7` (`DomainError`) + the `raise … from exc` rule. Applied in `_read_latest` (`export.py:116`), `_source_licence` (`repositories.py:853-858`). All new domain functions raise `DomainError` on an unknown licence, missing mapping row, or unknown value — never a silent skip.

### Operator CLI is the only write path
**Source:** `admin.py:140-168` (`_run_admin`). The push is `@acceslibre_app.command("push")`; no HTTP endpoint mutates data (AGENTS.md). `commit=False` = rollback for `--dry-run`.

### Append-only journal, losing value kept
**Source:** `repositories.py:1098-1133` (journal list) + `models.py:326-350` (`place_accessibility_write`). The push journal is a new table with the same "value kept, decision + reason" shape.

### Streaming (never materialise)
**Source:** `export_repositories.py:46-48` (`_PAGE = 1000`, `yield_per`), `export.py:176-178` (`_aiter`). The owned-row stream and the projection follow this — 634k places / 1.7M answers.

### Secrets
**Source:** `config.py:13` (`env_prefix="LETMEGETIN_"`). New `LETMEGETIN_ACCESLIBRE_API_KEY` lives in Infisical only (`AGENTS.md`); never a value in the repo. The adapter redacts it from logs/exceptions (V7).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `infrastructure/acceslibre/client.py` | infrastructure adapter | HTTP request-response | httpx is dev-only today; no runtime outbound HTTP adapter exists. Use the RESEARCH `MockTransport` stub + `config.py` settings pattern. |
| `tests/integration/acceslibre/test_client.py` (+ `fakes.py`) | integration test | — | No HTTP-client integration test exists (existing integration tests are API/seed). Use the RESEARCH stub shape; kind = integration (boundary mocked). |

## Metadata

**Analog search scope:** `src/letmegetin/{application,domain,infrastructure}/`, `migrations/versions/`, `tests/{unit,integration,functional}/`, `data/referential/`, `admin.py`, `config.py`, `core/exceptions.py`.
**Files scanned:** 19
**Pattern extraction date:** 2026-11-15
**GitNexus note:** index is stale (HEAD `0cd76ad` vs indexed `64d2b27`); re-run `node .gitnexus/run.cjs analyze --index-only` before trusting impact answers on `export.py` / `repositories.py` edits.
