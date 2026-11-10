# Linear — LetMeGetIn

Dedicated workspace: **`letmegetin`** (https://linear.app/letmegetin).
The exStrat people do not work on LetMeGetIn.

Team: **LET**

**Mapping GSD → Linear:**
- GSD **milestone** (`V1`, `V2`…) → Linear **project**.
- GSD **phase** → Linear **issue** (`LET-<n>`).
- **No Linear milestones**: a Linear milestone is a sub-checkpoint inside a project and has
  no GSD equivalent, so we do not use them (the project *is* the milestone).
Current milestone: **V1.1 — Production & Quality** (tickets LET-23, LET-33, LET-34, LET-35). V1 (LET-5..LET-12) is shipped.
Create a new project for each new GSD milestone.

**Linear is link-only**: it may link existing branches/PRs, but it must **never create**
them. Branches are created manually as `LET-<n>-…` so the `commit-msg` hook, the stack
and the no-auto-merge rule apply. Disable branch/PR automations in
Settings → Integrations → GitHub → Automations.

Every branch, commit and PR starts with the ticket id (`LET-<n>`).

**Never predict a ticket id in the planning docs.** Linear assigns the next free
number, so a roadmap that promises `LET-24` will point at nothing once another
ticket takes that slot. Create the ticket first, then write its real id here (this
is how phases 9-11 ended up as LET-33/34/35 instead of LET-24/25/26).

| Ticket | Phase | Scope |
|---|---|---|
| LET-5 | — | App - Bootstrap LetMeGetIn + Linear/GSD conventions |
| LET-6 | Phase 1 | Backend - Phase 1: Foundation & CI (FastAPI + PostGIS + Alembic + CI) |
| LET-7 | Phase 2 | Backend - Phase 2: Referential & seed |
| LET-8 | Phase 3 | Backend - Phase 3: Places & search |
| LET-9 | Phase 4 | Backend - Phase 4: Record & reviews (read) |
| LET-10 | Phase 5 | Backend - Phase 5: Auth & contribution |
| LET-11 | Phase 6 | Front - Phase 6: Next.js frontend |
| LET-12 | Phase 7 | Backend - Phase 7: Public API & deployment |
| LET-23 | Phase 8 (V1.1) | Ops - Production deployment & operations |
| LET-33 | Phase 9 (V1.1) | Backend - Data quality & curation |
| LET-34 | Phase 10 (V1.1) | Backend - Search quality |
| LET-35 | Phase 11 (V1.1) | Tooling - E2E & accessibility |
| LET-64 | — (V1.1) | Front - Landing page publique sur letmegetin.org |
| LET-27 | — | Tooling - GitNexus code intelligence |

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
