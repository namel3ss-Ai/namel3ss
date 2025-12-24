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

Bindings map English tool names to Python entry points (with optional metadata):

```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
```

Optional fields include `purity` and `timeout_ms`.

Generate bindings with Studio Tool Wizard or `n3 tools bind --from-app`.

## Tool kinds

### python
- Runs a Python function in `tools/*.py`.
- Executes in the app's `.venv` when present, otherwise uses system Python.
- Inputs and outputs are validated against the tool's `input`/`output` fields.

### builtin (AI tool calls)
- Used for model tool calls (e.g., `echo`).
- Not directly callable from flows.

## Tool calls

```ai
flow "demo":
  let result is greet someone:
    name is "Ada"
  return result
```

## Notes
- Python tools are the only tool kind callable from flows in v0.1.x.
- Tool payloads must be JSON objects; fields must match the declaration.
- Optional fields use `optional`, e.g. `age is optional number`.

## n3 tools commands

```bash
n3 tools status [app.ai]           # inspect bindings + missing/unused
n3 tools bind "<tool name>" --entry "module:function"
n3 tools bind --from-app [app.ai]  # generate bindings + stubs
n3 tools unbind "<tool name>"
n3 tools format                    # normalize tools.yaml
```
