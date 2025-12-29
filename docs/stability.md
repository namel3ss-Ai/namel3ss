# Stability

namel3ss is in alpha and focused on predictable change.

## Stable now
- CLI entrypoints for app, check, lint, format, ui, actions, studio
- Core declarations for records, flows, pages, tools, ai profiles, agents, and modules
- Compute core with define function, operators, bounded loops, list values, and map values
- Deterministic traces and execution steps
- Memory governance and memory packs
- Tool capability enforcement and purity gating
- Module reuse with use module
- Deterministic parallel blocks

## Compatibility promise
- Parser and IR outputs are locked by golden tests
- Trace contracts are locked by golden tests
- Deterministic runs stay stable for identical inputs
- Line limit checks keep files small

## May change
- New UI layout primitives and styling options
- Formatting details and lint rules
- Templates and examples as we learn

## Breaking changes policy
- No silent breaks
- Deprecations are announced in lint and format
- File first workflow stays stable
- Type canon uses text, number, boolean, and json
