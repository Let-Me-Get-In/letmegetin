# Linear — LetMeGetIn

> **Workspace dédié** (différent de `exstrat` : les gens d'exStrat ne travaillent
> pas sur LetMeGetIn). À créer dans l'UI Linear, puis :
> `linear auth login --workspace <slug> --key <API_KEY>`
> `linear config --team LMG --sort manual` (écrit `.linear.toml`)

Team: **LMG** • Project: **LetMeGetIn**

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
linear auth list
linear issue list --team LMG --all-states
linear issue create -t "…" --team LMG --project LetMeGetIn -a @me
linear issue update LMG-3 --state "In Progress"
linear issue url LMG-3
```
