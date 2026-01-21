# Data

namel3ss stores application data deterministically with explicit schemas, stable artifacts, and inspectable state.

## Backends
- Built-in adapters: SQLite, Postgres, MySQL.
- Target selection: `persistence.target` in `namel3ss.toml` or `N3_PERSIST_TARGET`.
- Connection strings: `N3_DATABASE_URL` for Postgres and MySQL.
- Drivers: install `namel3ss[postgres]` or `namel3ss[mysql]` for database connections.
- Edge is reserved for adapter packs; a pack can register a backend without changing the runtime.

## Replicas
- Optional `replica_urls` list in `namel3ss.toml` or `N3_REPLICA_URLS`.
- Replica values are used for inspection and routing hints; they are redacted in outputs.

## Migrations
Deterministic migrations are generated from record schema changes:
- `n3 migrate plan` writes a stable plan under `.namel3ss/migrations/`.
- `n3 migrate status` reports plan id, pending state, breaking flags, and reversibility.
- `n3 migrate apply` records the plan and updates the schema snapshot.
- `n3 migrate rollback` is allowed only for reversible plans; breaking changes require a new plan or a data export/import.

## Promotion safety
`n3 ship` detects pending migrations and plan changes before promotion.
- Apply migrations first, or use `n3 ship --with-migrations` to apply explicitly.

## Data export and import
Snapshots are deterministic and ordered:
- `n3 data export` returns stable JSON (use `--out` to write a file).
- `n3 data import <file>` applies a snapshot and reports a deterministic summary.
- Export/import summaries are stored under `.namel3ss/data/` and shown in Studio.

## Determinism and redaction
- Outputs are canonical JSON with stable ordering.
- No timestamps in stable payloads.
- Secrets, connection strings, and host paths are redacted.
