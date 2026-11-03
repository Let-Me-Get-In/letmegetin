# Project rules — applies to GSD workflows and their subagents

`AGENTS.md` at the repo root is authoritative and covers everything else. The
rules below are the ones GSD's own templates most often contradict, so they win
over any workflow, planner, executor or ship prompt that says otherwise.

## Linear tickets

- **Every branch, commit and PR starts with a Linear ticket id** `LET-<n>`.
  - Branch: `LET-<n>-<short-slug>` (e.g. `LET-6-socle-ci`).
  - Commit: `LET-<n> <type>(<scope>): <description>`.
  - PR title: `LET-<n> <type>(<scope>): <description>`.
- The `.githooks/commit-msg` hook prepends the ticket from the branch and rejects
  messages that do not conform. Do not bypass it with `--no-verify`.
- The roadmap ↔ tickets mapping lives in `.planning/LINEAR.md`.

## Branches and pull requests

- **Never commit to `main`.** Work on a `LET-<n>-…` branch.
- **One logical concern per PR.** Related or dependent changes are a **stack**,
  built with `gh stack init` / `gh stack add` / `gh stack submit --open` — never
  hand-rolled `gh pr create --base <layer>`.
- **Never merge.** Stop once CI is green and the PRs are ready for review. No
  `gh pr merge`, no `gh stack merge`, no merge button, not "to be helpful".
- **PR descriptions follow `.github/PULL_REQUEST_TEMPLATE.md`** when present:
  `What this changes` / `Why` / `How it works` / `Tests`, plus `Notes` only when
  it applies. Written by hand and short — never a dump of the commit list.

## Commit subjects

`LET-<n> {type}({feature}): {description}` — Conventional Commits after the
ticket, imperative, lowercase, no trailing period, under 72 characters.

- The scope names the **feature**, never the phase number: `feat(api)`,
  `fix(search)`, `docs(referential)`. **Not** `feat(01-02)` or `feat(02-01)` —
  a reader without `.planning/` open must still understand the commit.
- Keep the GSD plan id in the body on its own `Plan: 01-02` line, where it stays
  greppable with `git log --grep="Plan: 01-02"`.
- GSD's templates write `{type}({phase}-{plan})`; translate it — the plan id
  moves to the body, the subject gets the feature name.
- **A literal commit message inside a GSD workflow is a template, not a command
  to run verbatim.** `discuss-phase` hardcodes
  `docs(${padded_phase}): capture phase context` and
  `docs(state): record phase ${PHASE} context session`; run them as
  `LET-<n> docs(<feature>): capture the <topic> decisions` and
  `LET-<n> docs(state): record the <feature> discussion session`. Check every
  `gsd_run query commit "…"` before running it.

## GSD git settings

- `git.branching_strategy` is `none`: GSD must not create `gsd/phase-…` branches.
  All work happens on `LET-<n>-…` branches.

## Infisical — one project only

- Production secrets live in the single Infisical project
  **`39c0bbf4-d1c8-476e-ae35-8d82c998d704`** (`env=prod`, `path=/`,
  `domain=https://eu.infisical.com`). The id is pinned in `AGENTS.md`,
  `deploy/infisical.env.example` and enforced by `scripts/with-secrets.sh`.
- Run production commands through `./scripts/with-secrets.sh <cmd>`; never
  `--env-file deploy/.env.prod` on a server, never export secrets by hand.
- Do not create another Infisical organization or project for this repo, and do
  not read secrets from a different project id — the wrapper refuses it.
- Changing a secret requires restarting the containers that read it.
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
