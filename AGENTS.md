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

**Ticket titles carry an area prefix** — `<Area> - <title>`, so the board is
readable without opening a ticket. Areas in use: `Config` (the
`letmegetin-config` repo), `Backend`, `Front`, `Ops`, `Tooling`, `App`.
Examples: `Config - Phase 3: Host baseline`,
`Front - Phase 6: Next.js Frontend`. The prefix is cosmetic: it never replaces
the ticket id, which stays the first token of branch, commit and PR.

**Linear is link-only.** Linear may *link* existing branches/PRs, but it must
**never create** them: branches are created manually as `LET-<n>-…` so the
`commit-msg` hook, the stack and the no-auto-merge rule apply. Disable the
GitHub integration's branch/PR automations in Linear
(Settings → Integrations → GitHub → Automations).

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
- Coverage floor enforced in CI at **85 %** (line + branch).

## Commands

```bash
# Backend
docker compose up -d                 # PostGIS on localhost:55433
uv sync
git config core.hooksPath .githooks  # enable commit-msg + pre-commit hooks (once per clone)
uv run python scripts/build_referential.py
uv run alembic upgrade head
uv run python -m letmegetin.seed
uv run python -m letmegetin.admin --help    # operator CLI: the only write path (no auth yet)
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

Hooks: `git config core.hooksPath .githooks` is all a contributor needs — do
**not** run `pre-commit install` (it refuses when `core.hooksPath` is set). The
`.githooks/pre-commit` wrapper runs `uv run pre-commit run --hook-stage pre-commit`,
which mirrors the CI jobs (ruff, bandit, gitleaks, hygiene); `.githooks/commit-msg`
keeps enforcing the commit convention.

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
│   ├── main.py             # app FastAPI + /health
│   ├── seed.py             # seed loader (assumes `alembic upgrade head`)
│   ├── admin.py            # Typer CLI: categories, criteria, vocabulary, mapping, labels
│   ├── core/               # shared kernel: db.py, exceptions.py, utils.py
│   ├── domain/             # pure domain: entities + repository ports
│   │   ├── referential/    # categories, criteria, filters, grids
│   │   └── places/         # place aggregate, dedup scoring
│   ├── application/        # use cases (orchestration)
│   │   ├── referential/
│   │   └── places/         # acceslibre import, search, detail, candidates
│   ├── infrastructure/     # adapters: SQLAlchemy models, mappers, repositories
│   │   └── persistence/
│   └── api/                # presentation: deps, schemas, v1 endpoints
│       ├── deps.py
│       ├── schemas/
│       └── v1/
├── tests/
│   ├── unit/
│   └── integration/        # later (real PostGIS)
└── web/                    # Next.js (à venir)
```

**Layering (DDD):** `api → application → domain ← infrastructure`.

- `domain/` is pure (no SQLAlchemy, no FastAPI): entities + repository `Protocol`s.
- `application/` holds use cases; it depends only on the domain ports.
- `infrastructure/` implements the ports (SQLAlchemy `*Model`s, mappers, repositories).
- `api/` maps HTTP ↔ use cases; it never touches the ORM.

Write access goes through the operator CLI only: `letmegetin.admin` (same as
`python -m letmegetin.admin`) builds the SQLAlchemy repositories and calls the
`application/referential/admin.py` use cases. Until authentication exists (Phase
5), that CLI is the **only write path** to the referential — no HTTP endpoint
mutates data.

## Key design decisions

- **FastAPI** (not Django): async, OpenAPI auto; admin minimal then enriched.
- **PostGIS + JSONB i18n**: native geo search, simple multilingual labels.
- **Reconstructed seed** (no historical dump exists): category-1 grid as the
  universal base, extended and editable.
- **V1 scope**: referential + read API + place detail + contribution.
  Gamification, messaging and mobile are deferred (v2).
- **Places are France-first**: Acceslibre (Etalab 2.0) is the primary seed,
  imported from a local export; Overture/OSM stay additive via `place.source` and
  `category_mapping`. Never Google Places (its ToS forbids storing the data).
- **Dedup is soft**: `place.canonical_id` + `place_alias` + `place_merge_log`
  (auto-link ≥ 0.90, review 0.60–0.90, nothing is ever deleted). Name scoring is
  stdlib `difflib` on normalized names — no extra dependency.
- **4 handicap families** (`moteur`, `auditif`, `visuel`, `mental`) are data on
  criteria, not hard-coded in the API; `?family=` filters search.
- **Grids are precomputed**: `category_grid` holds the resolved per-category tree,
  invalidated by `referential_version` (`ETag: W/"ref-<version>"`, `304`).

## Security

- Never commit secrets; `.env` is git-ignored.
- The historical CSV/dump sources are private data — do not publish them.

### Secrets — Infisical (one project, never another)

Production secrets live in **exactly one** Infisical project:

```
INFISICAL_PROJECT_ID=264a35e3-cdca-43b7-9bdd-ff437c5bf2e1
INFISICAL_ENVIRONMENT=prod
INFISICAL_PATH=/
INFISICAL_DOMAIN=https://eu.infisical.com
```

- The project id is **not** a secret — it is pinned here and in
  `deploy/infisical.env.example` so nobody creates or reads from a second project
  (personal, staging, another product).
- Every production command goes through `./scripts/with-secrets.sh <cmd>`, which
  logs in with the machine identity and runs
  `infisical run --projectId … --env prod --path /`. Never `--env-file` a
  `deploy/.env.prod` on a server; never export secrets by hand.
- The host holds only `/etc/letmegetin/infisical.env` (machine identity, mode
  600). If its `INFISICAL_PROJECT_ID` differs from the value above, **stop and fix
  it** — do not run the command against that project.
- A new secret goes in the Infisical project above, in `prod` at `/`; changing a
  value requires restarting the containers that consume it (`infisical run`
  injects at process start).
- Never create a new Infisical organization or project for this repo: projects in
  the existing org are enough, and an extra one silently splits the secrets.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **letmegetin** (2231 symbols, 4310 relationships, 185 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/letmegetin/context` | Codebase overview, check index freshness |
| `gitnexus://repo/letmegetin/clusters` | All functional areas |
| `gitnexus://repo/letmegetin/processes` | All execution flows |
| `gitnexus://repo/letmegetin/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
