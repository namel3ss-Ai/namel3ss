# IR Executor Contract

This document defines the deterministic native IR executor boundary.
The Python runtime remains the semantic oracle.

## Scope

- Input: canonical lowered IR JSON bytes (see `namel3ss.ir.serialize.dump_ir`).
- Output: canonical runtime result JSON bytes matching the Python oracle.
- Execution is opt-in via `N3_NATIVE_EXEC`.

## Inputs

- `ir`: canonical IR JSON bytes.
- `config`: JSON bytes with the following keys:
  - `flow_name`: required string; selects the flow to execute.
  - `runtime_theme`: string or null; copied into the result.
  - `theme_source`: string or null; copied into the result.

## Outputs

The executor returns a canonical JSON object with stable ordering:

- `state`
- `last_value`
- `execution_steps`
- `traces`
- `runtime_theme`
- `theme_source`

The output must be deterministic, ASCII-safe, and free of host paths or secrets.

## Status Codes

- `OK`: execution succeeded; output is returned.
- `NOT_IMPLEMENTED`: IR contains unsupported operations.
- `INVALID_ARGUMENT`: malformed IR or config.
- `INVALID_STATE`: runtime state violation.
- `ERROR`: internal failure.

## Determinism Rules

- Identical inputs produce identical outputs.
- No time, randomness, environment access, filesystem access, or network access.
- Ordering of steps and maps is canonical and stable.

## Forbidden Behaviors

- Redefining meaning relative to the Python oracle.
- Partial execution for unsupported IR.
- Emitting host paths, timestamps, or secrets.
