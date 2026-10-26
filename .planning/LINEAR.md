# Linear — LetMeGetIn

Workspace dédié : **`letmegetin`** (https://linear.app/letmegetin).
Les gens d'exStrat ne travaillent pas sur LetMeGetIn.

Team: **LET** • Project: **LetMeGetIn**

Every branch, commit and PR starts with the ticket id (`LET-<n>`).

| Ticket | Phase | Scope |
|---|---|---|
| LET-5 | — | Bootstrap LetMeGetIn + conventions Linear/GSD |
| LET-6 | Phase 1 | Socle & CI (FastAPI + PostGIS + Alembic + CI) |
| LET-7 | Phase 2 | Référentiel & seed |
| LET-8 | Phase 3 | Lieux & recherche |
| LET-9 | Phase 4 | Fiche & avis (lecture) |
| LET-10 | Phase 5 | Auth & contribution |
| LET-11 | Phase 6 | Frontend Next.js |
| LET-12 | Phase 7 | API publique & déploiement |

## CLI

```bash
linear auth list
linear issue list --team LET --all-states
linear issue create -t "…" --team LET --project LetMeGetIn -a @me
linear issue update LET-7 --state "In Progress"
linear issue url LET-7
```

`.linear.toml` (workspace `letmegetin`, team `LET`) is written by
`linear config --team LET --sort manual --workspace letmegetin`.
