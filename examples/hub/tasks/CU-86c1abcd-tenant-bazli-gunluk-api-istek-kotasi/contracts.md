# Contracts — CU-86c1abcd

## Quota status endpoint

- Producer: backend
- Consumer: frontend

### Shape

```json
{ "limit": 1000, "used": 240, "remaining": 760, "resets_at": "2026-10-31T00:00:00Z" }
```

### Rules

- `GET /api/tenants/{id}/quota`, 200 on success, 404 when the tenant does not exist.
- `remaining` is never negative.
- A request rejected by the quota returns 429 with `Retry-After` in seconds, capped at 3600.

### Versioning

Additive only. A new field may be added; no field is removed before v2 of this endpoint.
