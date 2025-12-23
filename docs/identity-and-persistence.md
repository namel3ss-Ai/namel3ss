# Identity and Persistence

Phase 4 adds identity declarations, access controls, and environment-driven persistence targets.

## Identity basics

Declare who exists, then reference identity fields in flows and guards:

```ai
identity "user":
  field "email" is text must be present
  field "role" is text must be present
  trust_level is one of ["guest", "verified", "internal"]

flow "delete_order": requires identity.role is "admin"
```

Identity values come from config, not `.ai`:

- `N3_IDENTITY_JSON='{"email":"dev@example.com","role":"admin"}'`
- `N3_IDENTITY_EMAIL=dev@example.com` (prefixed env vars)

## Requires (authorization)

You can guard flows and pages:

```ai
flow "admin_report": requires identity.role is "admin"

page "admin": requires identity.role is one of ["admin", "staff"]
```

If the requirement fails, the runtime returns a clear guidance error.

## Persistence targets

Select a target in the environment (no secrets in `.ai`):

- SQLite (local dev): `N3_PERSIST_TARGET=sqlite` (optional `N3_DB_PATH`)
- Postgres (prod): `N3_PERSIST_TARGET=postgres` and `N3_DATABASE_URL=postgres://...`
- Edge (placeholder): `N3_PERSIST_TARGET=edge` and `N3_EDGE_KV_URL=...` (stub for now)

Check status with `n3 data`. If something fails, start with `n3 doctor`.

## Config precedence

Config loads from these sources (highest wins):

1) Environment variables
2) `.env` next to `app.ai`
3) `namel3ss.toml` (non-secret defaults)

Defaults apply when no config is provided.
