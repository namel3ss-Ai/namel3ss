# CLI: when

`n3 when` checks the program spec against the engine and writes a deterministic proof pack.

## What it is
- A spec compatibility check between the program and the engine.
- A stable summary of required and unsupported capabilities.

## What it includes
- Declared spec version.
- Engine supported spec versions.
- Required capabilities derived from the IR.
- Unsupported capabilities (if any).
- A compatible/blocked result.

## What it does NOT include
- Runtime behavior changes.
- Inferred causes beyond declared spec and IR facts.

## Artifacts
Artifacts are managed by namel3ss. Use `n3 status` for the last run summary,
`n3 explain` for failures, and `n3 clean` to remove runtime artifacts.
