# Conditional UI contract

## Scope
This document defines deterministic conditional visibility for UI blocks.

## Semantics
- `when` and `visible_when` are aliases for a visibility predicate.
- Predicates may reference `state.<path>` only.
- Evaluation is deterministic: a predicate is true only when the state path exists and is truthy.
- Visibility is compositional: child visibility is gated by parent visibility.

## Allowed state reads
- Only `state.*` paths are allowed.
- No expressions, operators, or function calls.
- No tool access or flow invocation.

## Explain output behavior
- Explain output includes the predicate text, state paths read, and the evaluation result.
- Elements remain in the manifest with `visible: true|false`.
- Actions are emitted only for elements that are visible.

## Invalid conditions
- Invalid predicates fail deterministically with explicit diagnostics.
- Errors include a clear fix and do not fall back to implicit behavior.
