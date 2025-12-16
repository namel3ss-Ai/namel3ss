# Runtime Model

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

## Records runtime
- `save`: validates current `state.<record_name>` dict against schema and writes to store.
- Validation errors raise `Namel3ssError` with context; uniqueness is checked via store lookup.
- `find`: runs a predicate over records in store, binding `<record>_results`.

## UI runtime actions
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

## AI runtime
- Explicit boundary: AI calls use profiles with model + system prompt.
- Tool loop guardrails: max tool calls per AI response; only exposed tools callable.
- Tracing: `AITrace` captures system prompt, input, output, memory context, tool calls/results.
- Memory: `MemoryManager` recalls context and records interactions (short/semantic/profile memory depending on profile).
