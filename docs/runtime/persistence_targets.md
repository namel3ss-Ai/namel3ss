# Persistence, Migrations, and Runtime Targets

Namel3ss persistence is configured in runtime config (`[persistence]`) and never auto-selected.

## Backends

- `memory`: in-process, non-durable.
- `sqlite` (file backend): deterministic local durable backend.
- `postgres` (network backend): durable backend for long-running service deployments.

`mysql` is treated as a network SQL backend in descriptor surfaces.

## Migration Contract

Runtime migration status is deterministic and additive:

- `state_schema_version`
- `migration_status`
- `persistence_backend`

CLI:

- `n3 migrate --status`
- `n3 migrate --dry-run`
- `n3 migrate --json`

Legacy migration subcommands remain available (`n3 migrate plan|apply|status|rollback`).

## Runtime Targets

Explicit targets:

- `local`
- `service`
- `embedded`
- `edge`

`embedded` runs the app in-process without starting an HTTP server.

## State Inspection

CLI state tooling:

- `n3 state list`
- `n3 state inspect <key>`
- `n3 state export`

Studio renders a read-only `state_inspector` element from runtime-provided persistence and migration metadata.
