# Threat Model: Memory and Storage

## Assets
- Memory items (redacted previews and metadata)
- Memory policies and governance records
- Persistence descriptors and store metadata
- Lineage for memory writes and recalls

## Trust Boundaries
- Runtime -> memory store
- Memory policy -> memory mutations
- App scope -> storage scope

## Threat Classes
- Contamination
- Disclosure
- Drift
- Replay
- Spoofing
- Tampering

## Mitigations
- Memory policy gates and audit traces (docs/memory-policy.md, docs/memory.md)
- Deterministic memory event traces and canonical ordering (docs/trace-schema.md)
- Redaction for memory previews and trace outputs (docs/memory.md, docs/observability.md)
- Scoped persistence and path scrubbing (docs/identity-and-persistence.md, docs/language/backend-capabilities.md)
