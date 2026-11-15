# Deferred items — Phase 15

Out-of-scope discoveries, not fixed by the plan that found them.

## 15-06 (dual licence)

- **`tests/functional/places/test_provenance.py` leaves the licence tables empty.**
  `test_backfill_resolves_every_source_from_reviewed_data` downgrades to `0010` and upgrades to
  `head`, which drops and recreates `licence`, `licence_destination` and `source_licence` with no
  rows. Any later suite that needs the destination matrix without syncing it itself fails
  (`test_acceslibre_push.py` does: 8 failures when run after provenance in the same session).
  The full suite stays green today only because `places/` sorts before the suites that re-sync.
  Fix belongs in the provenance fixture (re-seed after `upgrade head`), not in the licence plan.
