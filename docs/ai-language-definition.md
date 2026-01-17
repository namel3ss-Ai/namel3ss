# AI language definition

## What it means
Namel3ss is an AI programming language because AI is a first class runtime concept.
You define data, flows, tools, and memory in one file.
AI output is nondeterministic, but the boundary is explicit and traced.
Execution steps explain what happened and why.

## What is shipped now
- AI profiles and agent declarations
- Agent teams with deterministic ordering and optional roles
- AI calls with tool and memory integration
- Deterministic execution steps and traces
- Modules and memory packs for reuse
- Deterministic parallel blocks
- Compute core with define function, operators (including ** and between), bounded loops, list/map values, list aggregations, and map/filter/reduce

## What is intentionally missing
- Unbounded loops
- Hidden recursion
- Implicit type coercion
- Background tasks
- Silent tool or memory access

## Roadmap note
- This document is descriptive only; it makes no forward-looking commitments.
- Frozen contracts live in `docs/spec-freeze.md`.

## Related contracts
- [Application runtime](language/application-runtime.md)
- [Application Data Model](language/application-data-model.md)
- [No dependencies](language/no-dependencies.md)
- [Capability packs](language/capability-packs.md)
- [Browser Protocol](runtime/browser-protocol.md)
