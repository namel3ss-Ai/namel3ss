# Spec Freeze

## Contract status (public)
- Status: frozen
- Applies to: Expression Surface, UI Surface
- Freeze semantics: public contract; changes must be additive and explicitly documented

Namel3ss v1 contracts are frozen. These are the rules the engine, CLI, and tooling
must obey without breaking changes. When a breaking change is required, bump only
the relevant key in the canonical version map.

Canonical version map:
- resources/spec_versions.json

## Frozen contracts (v1)
- Language core (grammar + runtime semantics)
- Tool DSL (English-first declarations and calls)
- Tool protocol (local/service/container)
- Pack manifest + trust model
- Tool resolution precedence + collision rules
- UI DSL surface (docs/ui-dsl.md)
- UI manifest schema
- Identity schema + persistence config semantics
- Trace schema keys

Each contract is versioned in `resources/spec_versions.json`. Breaking changes
must increment the specific key only, with a changelog note.

## What may change (non-breaking)
- New language keywords that do not alter existing behavior
- New tool packs or runner options that are additive
- Additional fields in trace/UI/proof outputs (additive, optional)
- Docs/examples that do not alter engine behavior

## Version bumps
- Only bump the contract that changed.
- Keep `resources/spec_versions.json` as the source of truth.
- Update `CHANGELOG.md` with a short breaking-change note.

## Enforcement
- Executable spec suite under `spec/` (pass + fail)
- Invariant catalog under `resources/invariants.*`
- CI checks for legacy syntax, trace schema keys, and stable errors
