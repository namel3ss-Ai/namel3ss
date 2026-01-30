# Spec Freeze

## Contract status (public)
- Status: frozen
- Applies to: Expression Surface, UI Surface
- Freeze semantics: public contract; changes must be additive and explicitly documented

Namel3ss contracts are frozen. The authoritative list of frozen public contracts
is in `docs/contract-freeze.md`.

Canonical version map:
- resources/spec_versions.json

## Frozen contracts
See `docs/contract-freeze.md`.

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
