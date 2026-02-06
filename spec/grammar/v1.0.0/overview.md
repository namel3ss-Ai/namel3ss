# namel3ss language specification 1.0.0

This folder is the immutable specification for namel3ss language version 1.0.0.

## Files
- `namel3ss.grammar`: machine-readable grammar source.
- `overview.md`: human-readable semantics and guarantees.

## Scope
Version 1.0.0 formalises:
- Grammar structure
- Core type forms
- Runtime execution order
- Determinism guarantees

This version does not introduce new grammar keywords.

## Type system summary
Canonical types in this version:
- `text`
- `number`
- `boolean`
- `json`
- `list<...>`
- `map<...>`
- union types with `|`

## Runtime semantics summary
- Statements run top to bottom.
- Route matching is deterministic.
- Trace and output payloads use canonical ordering.
- Tool and model boundaries are explicit.

## Determinism summary
- The same source and inputs produce the same parse tree and IR.
- The same versioned grammar file always hashes to the same digest.
- Spec version files are immutable after publication.

## Governance notes
- Any grammar or semantic changes require an approved RFC.
- Changes are published as a new semantic version under `spec/grammar/vX.Y.Z/`.
