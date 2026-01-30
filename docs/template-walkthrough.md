# Template Walkthrough

## Template
Knowledge is a canonical template for retrieval-first systems.

## Lifecycle
- Ingest: normalize inputs and apply deterministic quality gates.
- Retrieve: select sources in a stable order.
- Answer: return cited responses or a clear no-answer outcome.
- Explain: surface why each source and decision was chosen.
- Update: apply incremental changes with auditable lineage.

## Observability and stability
- Observability is provided by structured logs, traces, and metrics (docs/observability.md).
- Stability guarantees and frozen contracts are defined in docs/contract-freeze.md.
- Breaking changes require explicit migration tooling and opt-in (docs/migration.md).
