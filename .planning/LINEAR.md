# Linear — LetMeGetIn

Dedicated workspace: **`letmegetin`** (https://linear.app/letmegetin).
The exStrat people do not work on LetMeGetIn.

Team: **LET**

**Mapping GSD → Linear:**
- GSD **milestone** (`V1`, `V2`…) → Linear **project**.
- GSD **phase** → Linear **issue** (`LET-<n>`).
- **No Linear milestones**: a Linear milestone is a sub-checkpoint inside a project and has
  no GSD equivalent, so we do not use them (the project *is* the milestone).
Current milestone: **V1 — Accessibility Referential** (tickets LET-5..LET-12).
Create a new project for each new GSD milestone.

**Linear is link-only**: it may link existing branches/PRs, but it must **never create**
them. Branches are created manually as `LET-<n>-…` so the `commit-msg` hook, the stack
and the no-auto-merge rule apply. Disable branch/PR automations in
Settings → Integrations → GitHub → Automations.

Every branch, commit and PR starts with the ticket id (`LET-<n>`).

| Ticket | Phase | Scope |
|---|---|---|
| LET-5 | — | Bootstrap LetMeGetIn + Linear/GSD conventions |
| LET-6 | Phase 1 | Foundation & CI (FastAPI + PostGIS + Alembic + CI) |
| LET-7 | Phase 2 | Referential & seed |
| LET-8 | Phase 3 | Places & search |
| LET-9 | Phase 4 | Record & reviews (read) |
| LET-10 | Phase 5 | Auth & contribution |
| LET-11 | Phase 6 | Next.js frontend |
| LET-12 | Phase 7 | Public API & deployment |

## CLI

```bash
linear auth list
linear issue list --team LET --all-states
linear issue create -t "…" --team LET --project "V1 — Accessibility Referential" -a @me
linear issue update LET-7 --state "In Progress"
linear issue url LET-7
```

`.linear.toml` (workspace `letmegetin`, team `LET`) is written by
`linear config --team LET --sort manual --workspace letmegetin`.
