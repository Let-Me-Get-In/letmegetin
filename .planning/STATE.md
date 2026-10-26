# State: LetMeGetIn

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-26)

**Core value:** Permettre à quiconque de savoir en quelques secondes si un lieu est réellement accessible.
**Current focus:** LMG-1 — Bootstrap + conventions (puis LMG-2, Phase 1)

## Current Position

Ticket: LMG-1 (Bootstrap LetMeGetIn + conventions Linear/GSD)
Phase: 1 of 7 (Socle & CI)
Plan: —
Status: In progress
Last activity: 2026-10-26 — Rename to LetMeGetIn, Linear team/project + tickets, AGENTS.md/CLAUDE.md, commit-msg hook.

## Performance Metrics

- Requirements: 26 v1
- Phases: 7
- Linear tickets: LMG-1..LMG-8
- Plans completed: 0

## Accumulated Context

### Decisions

- FastAPI + SQLAlchemy 2 async + PostGIS.
- Next.js (App Router) + TS + Tailwind + MapLibre.
- Seed reconstitué (pas de dump) ; grille cat-1 comme base.
- Monorepo back (racine) + front (`web/`) ; e2e dans un dépôt séparé plus tard.
- Linear team `LMG`, tickets `LMG-<n>` en tête de branche/commit/PR (hook `commit-msg`).
- GSD `branching_strategy = none` (pas de branches `gsd/phase-…`).

### Pending Todos

- Valider le seed (cf. `data/referential/`).
- Curer le vocabulaire complet (182 critères) en base (REF-05).

### Blockers/Concerns

- La grille exacte par catégorie n'est pas récupérable ; base + extension + admin.

## Session Continuity

Last session: 2026-10-26
Stopped at: rename + Linear + conventions
Resume file: .planning/PROJECT.md
