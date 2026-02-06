# Core Runtime and Language Evolution

This phase formalises the deterministic program model and extends ahead-of-time compilation.

## Program representation

The compiler now exposes a stable `ProgramRepresentation` contract in:

- `src/namel3ss/compiler/program_representation.py`

The structure is deterministic and serialisable:

- `spec_version`
- `records`
- `flows`
- `routes`

`n3 ast dump` continues to emit the existing `cir.v1` payload for compatibility and also includes:

- `representation_schema: "program_representation.v1"`

## Ahead-of-time compilation

`n3 compile` now supports:

- `c`
- `python`
- `rust`
- `wasm`

The Python target generates a deterministic module for pure numeric flows:

```bash
n3 compile --lang python --flow add --out dist
```

Generated module exports:

- `run_flow(input_json)`
- `run_flow_safe(input_json)`

## Determinism

- Program representation field order is canonical.
- Generated project files are written in sorted order.
- Re-compiling the same pure flow with the same target produces identical source output.
- No dynamic evaluation is introduced in compilation paths.
