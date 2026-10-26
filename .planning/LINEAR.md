# Linear — LetMeGetIn

Workspace: `exstrat` • Team: **LMG** (LetMeGetIn) • Project: **LetMeGetIn**

Every branch, commit and PR starts with the ticket id (`LMG-<n>`).

| Ticket | Phase | Scope |
|---|---|---|
| LMG-1 | — | Bootstrap LetMeGetIn + conventions Linear/GSD |
| LMG-2 | Phase 1 | Socle & CI (FastAPI + PostGIS + Alembic + CI) |
| LMG-3 | Phase 2 | Référentiel & seed |
| LMG-4 | Phase 3 | Lieux & recherche |
| LMG-5 | Phase 4 | Fiche & avis (lecture) |
| LMG-6 | Phase 5 | Auth & contribution |
| LMG-7 | Phase 6 | Frontend Next.js |
| LMG-8 | Phase 7 | API publique & déploiement |

## CLI

```bash
linear issue list --team LMG
linear issue create -t "…" --team LMG --project LetMeGetIn -a @me
linear issue update LMG-3 --state "In Progress"
linear issue url LMG-3
```

`linear config --team LMG --sort manual` wrote `.linear.toml`.
