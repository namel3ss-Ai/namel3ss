# Phase B4: when

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
Artifacts are written under:
- `.namel3ss/spec/last.json`
- `.namel3ss/spec/last.plain`
- `.namel3ss/spec/last.when.txt`
