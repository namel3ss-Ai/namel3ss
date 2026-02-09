# Engine Model

**Engine**: the system that runs a namel3ss app and enforces its rules.

## Execution model
- **state**: shared mutable dictionary (`ExecutionResult.state`) for persisted values (records, outputs).
- **locals**: per-flow environment; starts with `{"input": <input data>}`.
- **constants**: names declared with `let ... constant`; protected from reassignment.
- **last_value**: last evaluated statement result.
- **store**: backing persistence (`MemoryStore` by default) used by `save`/`find`.

## App lifecycle conventions (state-driven)
Lifecycle is a normal state value. There is no runtime automation.

Canonical values:
- "starting"
- "loading"
- "ready"
- "error"
- "stopped"

Example:
```
state:
  lifecycle is "starting"

flow "init":
  set state.lifecycle to "loading"
  set state.lifecycle to "ready"
```

Rules:
- Transitions are explicit and flow-driven.
- No implicit or automatic transitions.
- Same inputs produce the same lifecycle behavior.

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

## Browser development loop
- `n3 dev` starts a local browser loop with hot reload on save.
- Failures never render a blank screen; a dev overlay explains what happened, why, and how to fix it.
- Recovery is automatic after a successful rebuild; no manual refresh required.
- `n3 preview` renders a production-like UI locally without the dev overlay or reload affordances.

## Production server
- `n3 start` serves the production UI from build artifacts in `.namel3ss/build/`.
- No dev overlay, watcher, or preview markers are included.
- Run `n3 build --target service` before starting the production server.

## Service mode
- `n3 serve app.ai` and `n3 run --service app.ai` now share the same capability gate and behavior.
- Service mode requires `service`; concurrent sessions require `multi_user`; remote Studio inspection requires `remote_studio`.
- Session APIs are deterministic and role-scoped (`guest`, `user`, `admin`).
- See `docs/runtime/service-mode.md` for deployment, security, and remote Studio guidance.

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
- Structured input: maps/lists can be sent to AI calls and are serialized to canonical JSON with stable ordering; traces include the original structured data and the final text plus input_format.
- Memory: governed `MemoryItem` contract with space-aware recall/write, phase timeline, and explicit deletion/diff events (`memory_recall`, `memory_write`, `memory_denied`, `memory_conflict`, `memory_forget`, `memory_border_check`, `memory_promoted`, `memory_promotion_denied`, `memory_phase_started`, `memory_deleted`, `memory_phase_diff`). See `docs/memory.md`, `docs/memory-policy.md`, `docs/memory-spaces.md`, and `docs/memory-phases.md`.

## See also
- [Concurrency](concurrency.md) — parallel execution within flows.
- [Execution how](execution-how.md) — explainable execution and flow inspection.
- [Runtime error surfacing](runtime/runtime_errors.md) — canonical runtime error categories and diagnostics payloads.
- [Headless contracts](runtime/headless_contracts.md) — strict versioned API contract for `/api/v1` integrations.
- [Retrieval determinism](runtime/retrieval_determinism.md) — retrieval plan/trace and trust score evidence model.
- [Audit replay](runtime/audit_replay.md) — deterministic run artifacts, policy modes, and replay verification.
- [Persistence targets](runtime/persistence_targets.md) — deterministic persistence backends, migration lifecycle, and state inspection CLI.
