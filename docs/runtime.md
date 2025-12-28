# Engine Model

**Engine**: the system that runs a namel3ss app and enforces its rules.

## Execution model
- **state**: shared mutable dictionary (`ExecutionResult.state`) for persisted values (records, outputs).
- **locals**: per-flow environment; starts with `{"input": <input data>}`.
- **constants**: names declared with `let ... constant`; protected from reassignment.
- **last_value**: last evaluated statement result.
- **store**: backing persistence (`MemoryStore` by default) used by `save`/`find`.

## Flow execution
- `Executor.run()` walks a flow body in order.
- `return` raises an internal `_ReturnSignal` to stop execution and set `last_value`.
- `if`, `repeat`, `foreach`, `match`, `try/catch` mirror language control flow.
- Assignments target locals or `state.<path>`.

## Records engine
- `save`: validates current `state.<record_name>` dict against schema and writes to store.
- Validation errors raise `namel3ssError` with context; uniqueness is checked via store lookup.
- `find`: runs a predicate over records in store, binding `<record>_results`.

## UI engine actions
- `call_flow`: triggers a named flow (used by UI manifests).
- `submit_form`: validates incoming form data against record schema, returns structured errors on failure (`field`, `code`, `message`).
- Manifest regeneration: UI actions can rebuild manifests after state changes.

### Button syntax (block-only)
- Buttons must use a block:
  ```
  button "Run":
    calls flow "demo"
  ```
- One-line form (`button "Run" calls flow "demo"`) is rejected to avoid grammar chaos.

## AI engine
- Explicit boundary: AI calls use profiles with model + system prompt.
- Tool loop guardrails: max tool calls per AI response; only exposed tools callable.
- Tracing: `AITrace` captures system prompt, input, output, memory context, tool calls/results.
- Memory: governed `MemoryItem` contract with space-aware recall/write, phase timeline, and explicit deletion/diff events (`memory_recall`, `memory_write`, `memory_denied`, `memory_conflict`, `memory_forget`, `memory_border_check`, `memory_promoted`, `memory_promotion_denied`, `memory_phase_started`, `memory_deleted`, `memory_phase_diff`). See `docs/memory.md`, `docs/memory-policy.md`, `docs/memory-spaces.md`, and `docs/memory-phases.md`.
