# Namel3ss Specification

## Version
- `spec_version`: `namel3ss-spec@1`
- Status: frozen
- Normative language: this document uses **must**, **must not**, and **shall** as requirements.

## Scope
This specification defines the frozen behavior for:
- Grammar and parse surface
- Runtime semantics and determinism
- Retrieval and trust semantics
- Runtime/UI/headless contracts
- Runtime error taxonomy
- Audit and replay artifacts

## Spec Authority
The authoritative specification set for `namel3ss-spec@1` is:
- `docs/spec/grammar.md`
- `docs/spec/runtime_semantics.md`
- `docs/spec/retrieval_semantics.md`
- `docs/spec/contracts.md`
- `docs/spec/errors.md`

Implementation code **must** conform to these documents.

## Runtime Declaration
Runtime metadata and headless responses **must** include:
- `spec_version`
- `runtime_spec_version`

These values **must** be deterministic and stable for a released major line.

## Stability Rules
- Breaking changes **must not** ship without an explicit compatibility process.
- Additive fields are allowed when optional and backward compatible.
- Spec text for `namel3ss-spec@1` is immutable except for typo/clarity edits that do not change meaning.

## Change Process
- Any breaking proposal **must** include a new spec version.
- Any additive proposal **must** update relevant contracts/docs and tests.
- CI governance checks are mandatory and **must** pass.
