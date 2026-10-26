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
