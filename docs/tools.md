# Tools

Tools are explicit, named capabilities that run outside the language core. They are declared in `.ai` and called from flows. The `.ai` file stays intent-only; Python wiring lives in `.namel3ss/tools.yaml`.

## Tool declaration

```ai
tool "greet someone":
  implemented using python
  purity is "pure"
  timeout_seconds is 10

  input:
    name is text

  output:
    message is text
```

## Tool bindings (`.namel3ss/tools.yaml`)

Bindings map English tool names to Python entry points, plus runner metadata:

```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
    runner: "local"
    timeout_ms: 10000
```

Optional fields include `runner`, `url`, `image`, `command`, `env`, `purity`, and `timeout_ms`.

Generate bindings with Studio Tool Wizard or `n3 tools bind --auto`.
Built-in tool packs require no bindings.
Installed packs also provide their own bindings once verified and enabled.

## Tool runners

Runners determine where tool code executes:

- local (default): runs the Python subprocess locally (uses `.venv` if present).
- service: sends JSON to an HTTP tool service.
- container: runs the tool in a container (docker/podman required).

Service runner binding example:

```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
    runner: "service"
    url: "http://127.0.0.1:8787/tools"
```

Container runner binding example:

```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
    runner: "container"
    image: "ghcr.io/namel3ss/tools:latest"
    command: ["python", "-m", "namel3ss_tools.runner"]
    env: {"LOG_LEVEL": "info"}
```

You can also set a default service URL with `N3_TOOL_SERVICE_URL` or in `namel3ss.toml`:
```toml
[python_tools]
service_url = "http://127.0.0.1:8787/tools"
```

## Tool kinds

### python
- Runs a Python function in `tools/*.py`.
- Executes in the app's `.venv` when present, otherwise uses system Python.
- Inputs and outputs are validated against the tool's `input`/`output` fields.

### builtin (AI tool calls)
- Used for model tool calls (e.g., `echo`).
- Not directly callable from flows.

## Tool packs

Tools can also come from packs:
- built-in packs ship with namel3ss (pre-bound).
- installed packs live under `.namel3ss/packs/<pack_id>` and require verification + enable.

Use `n3 packs status` to see installed packs and `n3 packs enable <pack_id>` to activate a verified pack.
Pack tools show up in `n3 tools list` and `n3 tools search` with pack metadata.

## Tool calls

```ai
flow "demo":
  let result is greet someone:
    name is "Ada"
  return result
```

## Foreign boundaries (explicit extensions)

Foreign boundaries declare a typed, sandboxed function in the language and call it from a flow without adding a new expression language.

### Declaration

```ai
foreign python function "calculate_tax"
  input
    amount is number
    country is text
  output is number

foreign js function "format_currency"
  input
    amount is number
    currency is text
  output is text
```

### Call from a flow

```ai
flow "pricing"
  input
    amount is number
    country is text
  call foreign "calculate_tax"
    amount is input.amount
    country is input.country
```

### Types
- Allowed types: text, number, boolean, list of text/number/boolean.
- Inputs and outputs are validated at runtime and must match the declaration.

### Determinism policy
- Default mode allows foreign calls and traces the boundary.
- Strict mode blocks foreign calls unless explicitly allowed.
- Enable strict mode with `N3_FOREIGN_STRICT=1` or in `namel3ss.toml`:
  ```
  [foreign]
  strict = true
  ```
- Allow foreign calls in strict mode with `N3_FOREIGN_ALLOW=1` or:
  ```
  [foreign]
  allow = true
  ```

### Sandboxing and timeouts
- Foreign calls run in subprocesses (python or node).
- Network access is disabled by default.
- Filesystem access is limited to a safe workspace under `.namel3ss/foreign/<tool-slug>`.
- Timeouts use the tool timeout rules (default is 10s unless overridden).

### Explain + Studio parity
- Traces include `boundary_start`/`boundary_end` with deterministic input/output summaries.
- Manifest and Studio payloads include foreign intent (name, language, input schema, output type, policy mode).

## Notes
- Python tools are the only tool kind callable from flows in v0.1.x; foreign boundaries use `call foreign` instead.
- Tool payloads must be JSON objects; fields must match the declaration.
- Optional fields use `optional`, e.g. `age is optional number`.

## Tool status meanings
- ok: declared and bound (or provided by a built-in pack).
- missing binding: declared but not bound in `.namel3ss/tools.yaml`.
- unused binding: bound but not declared in `app.ai`.
- collision: binding conflicts with a pack tool name (or multiple packs provide the same tool).
- invalid binding: malformed entry or invalid runner configuration.
- unverified: installed pack is present but not verified.
- disabled: installed pack is verified but not enabled.

## n3 tools commands

```bash
n3 tools status [app.ai]           # inspect bindings + summary
n3 tools list [app.ai]             # list packs, declarations, bindings
n3 tools search "<query>" [app.ai] # search by tool name
n3 tools bind "<tool name>" --entry "module:function"
n3 tools bind --from-app [app.ai]  # generate bindings + stubs
n3 tools bind --auto [app.ai]      # alias of --from-app
n3 tools set-runner "<tool name>" --runner local|service|container
n3 tools unbind "<tool name>"
n3 tools format                    # normalize tools.yaml
```

## Capability id
runtime.tools
