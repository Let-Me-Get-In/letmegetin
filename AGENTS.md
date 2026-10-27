# AGENTS.md — LetMeGetIn

## Project overview

**LetMeGetIn** is the modern rewrite of Jaccede, the collaborative guide to
places accessible to people with disabilities. It exposes a **normalized
accessibility referential** (place categories, typed hierarchical criteria,
official labels) through a **public FastAPI API**, consumed by third parties and
by our own **Next.js** frontend.

**Monorepo (for now):**
- **Backend** — repo root: FastAPI, SQLAlchemy 2 async, Postgres/PostGIS.
- **Frontend** — `web/`: Next.js (App Router), TypeScript, Tailwind, MapLibre.
- **E2E** — later, in a **separate repo** (same model as interview-challenger).

## Tech stack

- **Language**: Python 3.12+ / TypeScript
- **Backend**: FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic, asyncpg
- **Database**: PostgreSQL 16 + PostGIS (`unaccent`), dev host port **55433**
- **Frontend**: Next.js (App Router), TypeScript, Tailwind, MapLibre/OSM
- **Package manager**: `uv` (Python), `npm` (web)
- **Quality**: ruff, mypy, bandit, pytest, pre-commit
- **Tracking**: Linear — **workspace dédié LetMeGetIn** (not `exstrat`), team **LET**, project **LetMeGetIn**

## Linear workflow (MANDATORY)

Every unit of work is tracked by a Linear ticket `LET-<n>` (team `LET`). The
ticket id is the **first token** of the branch name, the commit subject and the
PR title.

| Artefact | Format | Example |
|---|---|---|
| Branch | `LET-<n>-<short-slug>` | `LET-6-socle-ci` |
| Commit | `LET-<n> <type>(<scope>): <description>` | `LET-6 feat(api): add health endpoint` |
| PR title | `LET-<n> <type>(<scope>): <description>` | `LET-6 feat(api): add health endpoint` |

Rules:
- **Never** put the GSD phase number in the scope: `feat(01-02)` is forbidden.
  The scope names the feature (`feat(api)`, `fix(search)`, `docs(referential)`).
- Keep the GSD plan id in the commit **body** on its own line: `Plan: 01-02`.
- The **`.githooks/commit-msg` hook enforces this**: it prepends the ticket read
  from the branch and rejects phase-number scopes and non-conventional subjects.
- Create/update tickets with the Linear CLI (`.linear.toml` is written by
  `linear config` once the **dedicated workspace** is set up — not `exstrat`):
  ```bash
  linear issue create -t "…" --team LET --project LetMeGetIn -a @me
  linear issue update LET-7 --state "In Progress"
  linear issue list --team LET
  ```
- The roadmap ↔ tickets mapping lives in `.planning/LINEAR.md`.

## Branching model — GitHub Flow

- **NEVER commit or push directly to `main`.** Every change goes through a
  `LET-<n>-…` branch and a Pull Request.
- **Milestone delivery**: the milestone is one linear `gh stack`
  (`main ← LET-5 ← LET-6 ← …`), one phase per layer, merged bottom-up.
- **NEVER merge a PR automatically.** Stop when CI is green; merging is a human
  decision.
- **One logical concern per branch/PR.** Related, dependent changes are a
  **stack** built with `gh stack init` / `gh stack add` / `gh stack submit` —
  never hand-rolled `gh pr create --base <layer>`.
- Rebase, don't squash, when history matters.
- Delete the branch after merge (by the person who merges).

### PR description

Follow `.github/PULL_REQUEST_TEMPLATE.md` when it exists: `## What this changes`,
`## Why` (`Closes LET-<n>`), `## How it works`, `## Tests`, `## Notes` only when
relevant. Write it by hand, short; never dump the commit list.

## Commit conventions

```
LET-<n> <type>(<scope>): <description>
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`, `style`.
Imperative mood, lowercase, no trailing period, subject ≤ 72 characters.

Examples:
```
LET-6 feat(api): add health endpoint
LET-7 feat(referential): seed categories and criteria
LET-8 fix(search): return distance-sorted results
LET-6 docs(referential): document the reconstruction sources
```

## GSD workflow rules

- `.planning/` (GSD) is the planning source of truth: `PROJECT.md`,
  `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `LINEAR.md`.
- GSD runs with `git.branching_strategy = "none"`: it must **not** create
  `gsd/phase-…` branches. Work happens on `LET-<n>-…` branches.
- **A literal commit message inside a GSD workflow is a template, not a command
  to run verbatim.** Translate `docs(${phase}): …` into
  `LET-<n> docs(<feature>): …` and move the plan id to the body.
- Never let GSD emit `feat(01-02)`-style scopes; the hook will reject them.

## Code conventions

### Python
- `from __future__ import annotations` in every module.
- Type hints on all signatures; `str | None`, `list[...]`, `dict[...]`.
- Line length 100; imports sorted by ruff.
- SQLAlchemy 2.0 typed models (`Mapped[...]`, `mapped_column`).
- i18n: JSONB columns `{"fr": …, "en": …}`.
- No comments that restate the code; comment the *why*.
- Always `raise … from exc` in `except` blocks.

### TypeScript (web/)
- `strict` TypeScript, no `any` without a reason.
- Server Components by default; Client Components only when needed.
- Accessibility is a first-class requirement (this product is about it).

## Testing

- **Framework**: pytest (+ `pytest-asyncio`), `httpx`/`TestClient`.
- Layout: `tests/` (unit + integration); e2e later in a separate repo.
- Use `@pytest.mark.parametrize` for multi-case tests.
- Mock external boundaries (`mocker`), never call real APIs.
- AAA pattern; test names `test_<unit>_<scenario>`.
- Coverage floor enforced in CI (start at 80 %, raise over time).

## Commands

```bash
# Backend
docker compose up -d                 # PostGIS on localhost:55433
uv sync
git config core.hooksPath .githooks  # enable the commit-msg hook (once per clone)
uv run python scripts/build_referential.py
uv run alembic upgrade head
uv run python -m letmegetin.seed
uv run uvicorn letmegetin.main:app --reload
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run bandit -r src -c pyproject.toml

# Frontend (once web/ exists)
cd web && npm ci && npm run dev && npm run lint && npm run typecheck && npm run build

# Linear
linear issue list --team LET
```

## Architecture

```
letmegetin/
├── .planning/              # GSD (PROJECT, REQUIREMENTS, ROADMAP, STATE, LINEAR)
├── .githooks/commit-msg    # enforces Linear ticket + conventions
├── data/referential/       # seed reconstitué (categories, criteria, filters, th)
│   └── raw/                # sources historiques (archives, ne pas réécrire)
├── scripts/build_referential.py
├── src/letmegetin/
│   ├── config.py           # pydantic-settings (LETMEGETIN_*)
│   ├── db.py               # engine/session async
│   ├── models.py           # référentiel (Category, Criterion, …)
│   ├── schemas.py          # Pydantic v2
│   ├── api.py              # /api/v1/{categories,criteria,filters,other-information}
│   ├── seed.py
│   └── main.py             # app FastAPI + /health
├── tests/
└── web/                    # Next.js (à venir)
```

## Key design decisions

- **FastAPI** (not Django): async, OpenAPI auto; admin minimal then enriched.
- **PostGIS + JSONB i18n**: native geo search, simple multilingual labels.
- **Reconstructed seed** (no historical dump exists): category-1 grid as the
  universal base, extended and editable.
- **V1 scope**: referential + read API + place detail + contribution.
  Gamification, messaging and mobile are deferred (v2).

## Security

- Never commit secrets; `.env` is git-ignored.
- The historical CSV/dump sources are private data — do not publish them.
