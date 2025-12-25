# Python tools

Python tools let you run local Python functions from flows with explicit schemas, traceability, and deterministic defaults.

## Quick setup

1) Write code in `tools/*.py`:
```python
# tools/sample_tool.py
def greet(payload: dict) -> dict:
    name = payload.get("name", "world")
    return {"message": f"Hello {name}", "ok": True}
```

2) Declare the tool in `app.ai` (English name + input/output):
```ai
tool "greet someone":
  implemented using python
  purity is "pure"
  timeout_seconds is 10

  input:
    name is text

  output:
    message is text
    ok is boolean
```

3) Bind the tool to the Python entry point:
```bash
n3 tools bind "greet someone" --entry "tools.sample_tool:greet"
```
Or add it to `.namel3ss/tools.yaml`:
```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
```

4) Install dependencies (if any):
```bash
n3 deps install
```

5) Call the tool in a flow:
```ai
flow "hello":
  let result is greet someone:
    name is "Ada"
  return result
```

## Binding in 10 seconds

If you want zero wiring, let namel3ss generate bindings and stubs:
```bash
n3 tools bind --auto
```
This scans `app.ai`, creates `.namel3ss/tools.yaml`, and generates missing `tools/<slug>.py` stubs.

## Runners (local, service, container)

Python tools can run locally (default), via an HTTP service, or in a container.
Use `runner` in `.namel3ss/tools.yaml` or `n3 tools set-runner` to choose.

Local runner (default):
```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
    runner: "local"
```

Sandboxed local runner (enforced guarantees):
```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
    runner: "local"
    sandbox: true
```
Sandbox is required to enforce capability guarantees for user-defined tools.

Service runner:
```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
    runner: "service"
    url: "http://127.0.0.1:8787/tools"
```
You can also set a default URL with `N3_TOOL_SERVICE_URL` or in `namel3ss.toml`:
```toml
[python_tools]
service_url = "http://127.0.0.1:8787/tools"
service_handshake_required = true
```
Service runners should implement the capability handshake endpoint in
`/capabilities/handshake` to prove enforcement coverage.

Container runner:
```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
    runner: "container"
    image: "ghcr.io/namel3ss/tools:latest"
    command: ["python", "-m", "namel3ss_tools.runner"]
    env: {"LOG_LEVEL": "info"}
    enforcement: "declared"  # or "verified"
```

## Auto-bind via Studio

Studio can auto-bind and generate stubs for you:
1) Run Studio: `n3 app.ai studio`
2) Open **Tool Wizard**
3) Preview, then click **Create tool**

Studio will create the tool block, bind it automatically, and generate a stub if needed.

## Tool Wizard

Studio includes a Tool Wizard to generate a skeleton function, tool declaration, and binding:

1) Run Studio: `n3 app.ai studio`
2) Click **Tool Wizard**.
3) Fill in the tool name, purity, timeout, and schema fields.
4) Preview, then click **Create tool**.

Field format is `name:type`, one per line (use `?` for optional), e.g.:
```
name:text
age?:number
```

## Built-in tool packs

You can use built-in tool packs without writing Python. Declare the tool in English; built-in packs are pre-bound.

```ai
tool "slugify text":
  implemented using python

  input:
    text is text
    separator is optional text

  output:
    text is text
```

No bindings are required for built-in packs.

See [Tool packs](tool-packs.md) for available tools.

## Local tool packs (marketplace)

You can install packs from disk and use their English tools without wiring:
```bash
n3 packs add ./my_pack
n3 packs keys add --id "maintainer.alice" --public-key ./alice.pub
n3 packs verify my.pack
n3 packs enable my.pack
```
Use `n3 packs status` to see verification/enabled state.

See [Tool packs](tool-packs.md) for pack format and trust model.

## Dependency files

Supported in this order:
- `pyproject.toml` with `[project].dependencies`
- `requirements.txt`

If both exist, `pyproject.toml` is preferred and a warning is shown.

## Schemas

Schemas are minimal and explicit. Supported field types:
- `text`
- `number`
- `boolean`
- `json`

Use `input` and `output` blocks to define required fields. For optional fields, use `optional`, e.g. `age is optional number`.

## Purity

Use `purity is "pure"` for deterministic tools. Any side effects should be marked `impure` (default). Traces record impurity explicitly.

## Timeouts

Tools default to 10 seconds. Override per tool with `timeout_seconds` or set a global default in `namel3ss.toml`:
```toml
[python_tools]
timeout_seconds = 20
```

## Tool health

Use lint and status checks to catch binding issues and collisions early:
```bash
n3 tools status
n3 lint --strict-tools
```
Runner issues (missing service URL, missing container runtime/image) are flagged here as well.

## Troubleshooting

- Missing binding: run `n3 tools status`, then `n3 tools bind --auto`.
- Missing module/function: check `.namel3ss/tools.yaml` and ensure files live under `tools/`.
- Dependency errors: run `n3 deps status`, then `n3 deps install`.
- Timeout: increase `timeout_seconds` or optimize the tool.
- Output field errors: ensure the tool returns a JSON object matching the `output` fields.

## Tool subprocess protocol

The Python tool runner follows a small JSON protocol for stdin/stdout. See
[Python tool protocol](python-tool-protocol.md) for the canonical spec.
