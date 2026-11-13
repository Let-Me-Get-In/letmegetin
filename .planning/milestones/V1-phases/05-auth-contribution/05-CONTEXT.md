# Phase 5: Auth & Contribution — Context

**Gathered:** 2026-10-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Accounts and writes: a user signs up, logs in, completes a record's accessibility values, posts a
review; an admin can hide a review.

- `POST /api/v1/auth/register`, `/login`, `/refresh`, `GET /me`.
- `PUT /api/v1/places/{slug}/accessibility/{criterion_slug}` (auth) → value upserted + logged.
- `POST /api/v1/places/{slug}/reviews` (auth) → published review.
- `PATCH /api/v1/reviews/{id}` (admin) → hide/publish (the sensitive action AUTH-03 gates).

Out of scope: the Next.js UI (Phase 6), OAuth, email verification, password reset.
</domain>

<decisions>
## Decisions

- **No new dependency**: `hashlib.scrypt` for passwords, HS256 JWT signed with `hmac` from the
  standard library. Secret and TTLs live in settings (`LETMEGETIN_JWT_SECRET`, …).
- **Stateless refresh tokens**: both tokens carry a `typ` claim; `/refresh` verifies `typ=refresh`
  and issues a new pair. No token store, so no server-side revocation in the MVP.
- **`contribution` is an append-only audit log** (`user_id`, `place_id`, `criterion_id`, `value`).
  The current value stays in `place_accessibility`; writes upsert it and append a log row.
- **`filled_rate` is computed on read**, never stored: the write endpoint re-reads the record with
  `get_place` so the response carries the recomputed rate.
- **User-sourced values are marked** (`source: "user"`, `user_id`), so an Acceslibre re-import can
  avoid clobbering them later.
- **Author identity** comes from `display_name` (default `Anonyme`); the email is never exposed.
- **Admin gate**: `PATCH /reviews/{id}` is the first sensitive action; `require_admin` returns 403
  for `role=user`. Referential edits stay CLI-only, so no HTTP admin surface is invented.
</decisions>

<canonical_refs>
- `.planning/REQUIREMENTS.md` — AUTH-01/02/03, CONTRIB-01/02, REV-02.
- `.planning/ROADMAP.md` — Phase 5 success criteria.
- `.planning/phases/04-record-reviews/04-CONTEXT.md` — review/photo model and read contracts.
</canonical_refs>

<code_context>
- `get_place` returns the tree + `filled_rate`; `PlaceRepository.upsert_accessibility` already
  resolves criterion slugs and ignores unknown ones.
- `review` and `place_photo` exist (migration 0004); `review` has no `user_id` yet.
- Session handling is one `get_session` dependency; writes commit explicitly.
- Tests: unit fakes for use cases, integration against the PostGIS container.
</code_context>

<deferred>
- Refresh-token revocation, email verification, password reset, OAuth (Google/LinkedIn).
- Rate limiting on auth endpoints (Phase 7 / gateway).
</deferred>

---
*Phase: 05-auth-contribution*
