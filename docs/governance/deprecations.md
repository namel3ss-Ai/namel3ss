# Deprecation Policy

## Requirements
Deprecations **must** be explicit and deterministic.

Every deprecation **must** define:
- deprecation identifier
- affected surface
- first warning release
- planned removal release
- migration path

## Warning Behavior
- Deprecation warnings **must** be machine-readable.
- Warnings **must not** include nondeterministic metadata.
- Warnings **must** provide actionable migration hints.

## Removal Rules
- No immediate removals of stable surfaces.
- Removal **must** follow documented timeline and changelog notes.
