# Threat Model: Ingestion

## Assets
- Upload content (deterministic extraction with scrubbed previews)
- Ingestion reports (status, signals, preview)
- Chunk identifiers and provenance
- Indexing eligibility

## Trust Boundaries
- Upload input -> ingestion pipeline
- Ingestion pipeline -> index storage
- Policy decisions -> retrieval inclusion

## Threat Classes
- Contamination
- Disclosure
- Exhaustion
- Replay
- Spoofing
- Tampering

## Mitigations
- Deterministic extraction and quality gate (docs/runtime/ingestion.md)
- Explicit policy controls for overrides and warned retrieval (docs/runtime/ingestion.md)
- Blocked content never indexed or retrieved (docs/runtime/ingestion.md, docs/runtime/retrieval.md)
- Audit explain records gate and policy decisions (docs/trust-and-governance.md)
- Redaction and path scrubbing in previews and observability outputs (docs/observability.md)
