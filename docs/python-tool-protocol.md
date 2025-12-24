# Python tool protocol

Namel3ss runs Python tools in a subprocess using a small JSON protocol. This keeps
execution explicit, traceable, and easy to evolve.

## Protocol version

```
protocol_version: 1
```

## Stdin schema (tool runner input)

```json
{
  "protocol_version": 1,
  "tool": "greeter",
  "entry": "tools.sample_tool:greet",
  "payload": { "name": "Ada" }
}
```

Fields:
- `protocol_version` (number): current protocol version.
- `tool` (string): tool name from the `.ai` declaration.
- `entry` (string): module:function entry point.
- `payload` (object): JSON payload for the tool.

## Stdout schema (tool runner output)

Success:
```json
{
  "ok": true,
  "protocol_version": 1,
  "result": { "message": "Hello Ada", "ok": true }
}
```

Error:
```json
{
  "ok": false,
  "protocol_version": 1,
  "error": { "type": "ValueError", "message": "Missing input" }
}
```

## Exit codes

- Exit code `0`: tool completed and wrote a JSON response.
- Non-zero exit code with no stdout: the tool subprocess crashed; namel3ss raises a tool error.

## Timeouts

Tools are terminated after their timeout (default 10 seconds). Configure per-tool
with `timeout_seconds`, or set a global default in `namel3ss.toml`.

## Trace fields

Tool call traces include:
- `python_env`: `system` or `venv`
- `python_path`: interpreter path
- `deps_source`: `pyproject`, `requirements`, or `none`
- `protocol_version`: current tool protocol version
