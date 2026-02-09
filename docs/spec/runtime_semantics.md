# Runtime Semantics Specification

## Deterministic Execution
Given identical:
- program IR
- runtime config
- input payload
- persisted state

the runtime **must** produce identical:
- state transitions
- manifest payloads
- action payloads
- runtime error classifications

## Execution Model
The runtime **shall** evaluate in explicit phases:
1. Input resolution
2. Policy and capability checks
3. Flow/action execution
4. Retrieval and trust derivation (if applicable)
5. Response assembly
6. Optional audit capture

No phase **may** mutate prior phase outputs implicitly.

## State Semantics
- State writes **must** be explicit.
- Persistence writes **must** be ordered and deterministic.
- Missing required migrations **must** produce structured runtime errors.

## Audit and Replay
- Run artifacts **must** be immutable once written.
- Replay **must** use equivalent semantics and emit deterministic diff output on mismatch.
