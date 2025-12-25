# Python tool protocol

Namel3ss runs Python tools using a small JSON protocol (local subprocess and service runner).
This keeps execution explicit, traceable, and easy to evolve.

## Protocol version

```
protocol_version: 1
```

## Local subprocess schema (stdin)

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

## Local subprocess schema (stdout)

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

## Service runner schema (HTTP)

Request (POST JSON):
```json
{
  "protocol_version": 1,
  "tool_name": "greeter",
  "kind": "python",
  "entry": "tools.sample_tool:greet",
  "payload": { "name": "Ada" },
  "timeout_ms": 10000,
  "trace_id": "uuid",
  "project": { "app_root": "/path/to/app", "flow": "demo" }
}
```

Response (success):
```json
{ "ok": true, "result": { "message": "Hello Ada" } }
```

Response (error):
```json
{ "ok": false, "error": { "type": "ValueError", "message": "Missing input" } }
```

## Trace fields

Tool call traces include:
- `runner`: `local`, `service`, or `container`
- `resolved_source`: `builtin_pack`, `installed_pack`, or `binding`
- `timeout_ms` and `duration_ms`
- `protocol_version`: current tool protocol version
- local runner: `python_env`, `python_path`, `deps_source`
- service runner: `service_url`
- container runner: `container_runtime`, `image`, `command`
- pack tools: `pack_id`, `pack_name`, `pack_version`
