# Migration

Migrations are deterministic helpers that make breaking changes explicit and auditable. They never run automatically.

## Rules
- Migrations are idempotent.
- Migrations produce explainable diffs.
- Migrations do not apply changes without an explicit command.

## Tooling
- Contract migration helper: tools/contract_migrate.py
- The default mode is plan-only.
- Apply requires explicit flags and a target path.

## Output
- Outputs are ordered and stable.
- Outputs use repo-relative paths.
- Outputs contain no timestamps or host paths.
