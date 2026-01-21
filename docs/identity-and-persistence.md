# Identity and Persistence

Identity declarations, access controls, and environment-driven persistence targets for namel3ss apps.

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

## Authentication and sessions

Identity is resolved in this order:
1. Session cookie (`n3_session`)
2. Bearer token (`Authorization: Bearer <token>`)
3. Config defaults (`N3_IDENTITY_*` or `namel3ss.toml`)

Sessions are stored in the configured persistence backend and created via `POST /api/login`.
Session ids are never returned raw in JSON; only redacted values like `session:abc123...`.

Tokens can be issued by `POST /api/login` when a signing key is configured.
Verification is deterministic with categories: `valid`, `expired`, `revoked`.

## Requires (authorization)

You can guard flows and pages:

```ai
flow "admin_report": requires identity.role is "admin"

page "admin": requires identity.role is one of ["admin", "staff"]
```

If the requirement fails, the engine returns a clear guidance error.

Helpers can keep requires clauses readable:
- `has_role("admin")`
- `has_permission("reports.view")`

## Mutation access policy

Mutating flows (create, update, delete, save) must declare a `requires` rule.
`n3 check` warns when a mutating flow is missing access control; runtime blocks the mutation with a clear fix hint.
Pages with forms should also declare `requires`; form submissions are blocked without it.

`requires` rules can reference:
- `identity` (for user/session data)
- `mutation.action` (save, create, update, delete)
- `mutation.record` (record name)

Example:

```ai
flow "delete_order": requires identity.role is "admin" and mutation.action is "delete"
```

## Audit-required mode

When `N3_AUDIT_REQUIRED=1`, any mutating flow must be marked `audited`.
Missing `audited` blocks the mutation at runtime and produces a warning in `n3 check`.

```ai
flow "update_order": audited requires identity.role is "admin"
```

## Schema evolution and data contracts

Record schemas are snapshotted deterministically for compatibility checks:

- Runtime snapshot: `.namel3ss/schema/last.json`
- Build snapshot: `build/<target>/<build_id>/schema/records.json`

`n3 check` warns when the current schema is incompatible with the stored snapshot.
`n3 build` fails on breaking changes, and the runtime refuses to start when persistence is enabled.

Allowed changes:
- Add a new optional field (no required constraint).

Breaking changes:
- Remove or rename a record or field.
- Change a field type.
- Add a required field (`must be present` or any constraint that requires a value).
- Change constraints, `tenant_key`, or `ttl_hours`.

Ordering and ids:
- Record ids are stable once created (`id` or `_id`).
- `view of "<Record>"` defaults to deterministic ordering by id ascending (no time-based ordering).

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
