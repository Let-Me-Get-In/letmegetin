# Phase 15 — AccesLibre API Coverage

**Phase:** 15 — AccesLibre round trip
**Prepared:** 2026-11-15
**Source of truth:** live `/api/openapi` (HTTP 200, fetched 2026-11-15), upstream `api/views.py` / `api/urls.py` (`ErpViewSet.http_method_names = ["get","post","patch"]`, `lookup_field = "slug"`), `15-RESEARCH.md` §AccesLibre API contract.

Every capability the phase could touch is enumerated. A capability we will **not** call is an `OPT-OUT` with a one-line reason; everything we do call is `COVER` with the plan/task that builds and tests it.

## Matrix

| Capability | Endpoint | Decision | Reason / Usage |
|------------|----------|----------|----------------|
| `get-erp` | `GET /api/erps/<slug>/` | COVER | Read-then-diff (D-10): fetch the ERP's current `accessibilite` section before any PATCH. Built in plan 15-02 (adapter), driven by 15-04 (push). |
| `patch-erp` | `PATCH /api/erps/<slug>/` | COVER | The idempotent write-back (D-10/D-14). Payload `{"accessibilite": {…}}`, only fields that differ after typed normalisation. Plan 15-04. |
| `get-accessibility` | `GET /api/accessibility/<id>/` | OPT-OUT | The `get-erp` response already returns `accessibilite` inline (with a nested `url` to this endpoint); a second call would re-fetch data we already hold. No separate accessor is needed this phase. |
| `list-erps` | `GET /api/erps/` (search: `?source=`, `?source_id=`, `?uuid=`) | COVER | The read-only identifier probe (Open Question 1 / D-05): resolve which of `uuid` / `source_id` / our `origin_id` is the ERP `slug`. Built in plan 15-02 (probe command), gated on the API key. |
| `post-erp` | `POST /api/erps/` | OPT-OUT | We only push answers to ERPs we already imported (they exist upstream); D-14 is PATCH-only. Creating new ERPs is out of scope this phase. |
| `delete` | `DELETE /api/erps/<slug>/` (any) | OPT-OUT | Their business rules forbid deletion ("it is not possible to delete any data"); nothing in this phase deletes. |

## Notes

- **Auth:** `Authorization: Api-Key <key>` on every covered call; the key comes from settings (`LETMEGETIN_ACCESLIBRE_API_KEY`) via Infisical, never a repo value (D-13, AGENTS.md).
- **No key exists yet.** Every covered capability is built and tested against an `httpx.MockTransport` stub; the first real call is a blocking `checkpoint:human-action` (the probe, plan 15-02).
- **Write key confirmed by research:** the nested write object is `accessibilite` (not `accessibility`); the 8 `FIELD_MAP` fields are present in the write schema with types that differ from the read schema (typed normalisation, Pitfall 9).
