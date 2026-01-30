# Tool Validation

Tool inputs and outputs are validated against declared schemas. Validation is deterministic and fails fast on mismatches.

## Schema enforcement
- Payloads must be JSON objects unless the declaration specifies a single foreign output type.
- Required fields must be present.
- Field names must match the declared schema.
- Types are limited to text, number, boolean, and json (foreign functions use foreign type rules).

## Failure behavior
- Invalid payloads raise deterministic errors with what, why, and fix guidance.
- Payloads are not coerced or silently corrected.

## Redaction and size limits
- Error messages are redacted before rendering.
- Trace summaries use redacted previews and fixed length limits.
- Output summaries include type, key counts, and previews, not raw payloads.

## Determinism
- Schema validation does not use environment state.
- Summary keys are ordered deterministically.
