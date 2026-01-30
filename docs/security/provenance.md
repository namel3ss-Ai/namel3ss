# Provenance and Lineage

Provenance links inputs, decisions, and outputs through deterministic traces and audit records. Lineage provides stable identifiers that let operators reconstruct what happened without reading code.

## Provenance
- Tool call traces include tool name, decision, capability, and input/output summaries.
- Boundary events record foreign function inputs and outputs as summaries.
- Audit reports record policy decisions, inputs, and outcomes in a deterministic order.

## Lineage
- Trace hashes provide stable identifiers for a run's canonical trace set.
- Job identifiers and tool names bind actions to execution records.
- Summaries are redacted and deterministic; they never include raw secrets.

## Integrity
- Canonical trace JSON is ordered and excludes volatile keys before hashing.
- Trace hash values are stable across identical inputs.
