# Language Specification

namel3ss keeps a machine-readable language specification under version control.

## Source of truth
- Registry: `spec/grammar/registry.yaml`
- Current grammar file: `spec/grammar/v1.0.0/namel3ss.grammar`
- Current overview: `spec/grammar/v1.0.0/overview.md`

## Versioning rules
- Specification versions use semantic versioning.
- Each version is immutable after release.
- New grammar or semantic changes require an accepted RFC.

## Reference implementation
The compiler and runtime in this repository are the reference implementation.

## External tooling guidance
External parsers or language tools should:
- read the target version from the registry
- use the grammar for parsing
- follow the companion overview for semantics and determinism expectations
