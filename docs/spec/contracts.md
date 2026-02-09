# Runtime Contracts Specification

## Contract Versions
- Runtime/UI contract: `runtime-ui@1`
- Spec version: `namel3ss-spec@1`
- Runtime spec declaration: `runtime-spec@1`

## Response Metadata Requirements
Headless and runtime API envelopes **must** include:
- `contract_version`
- `spec_version`
- `runtime_spec_version`

These values **must** be deterministic and stable for a given release.

## Compatibility Model
- Additive optional fields are allowed.
- Removing required fields is breaking.
- Renaming fields is breaking.
- Type changes for existing fields are breaking.

## Canonical Schemas
The schema authority lives in:
- `src/namel3ss/runtime/contracts/runtime_schema.py`
- `src/namel3ss/runtime/contracts/action_schema.py`
- `src/namel3ss/runtime/contracts/ui_manifest_schema.py`

Compatibility checks **must** validate against the frozen baseline:
- `resources/runtime_contract_schema_v1.json`
