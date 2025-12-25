# Python tool protocol

Namel3ss runs Python tools using a small JSON protocol (local subprocess and service runner).
This keeps execution explicit, traceable, and easy to evolve.

## Protocol version

```
protocol_version: 1
```

Tool protocol is frozen at `tool_protocol` v1 (see `resources/spec_versions.json`).

## Local subprocess schema (stdin)

```json
{
  "protocol_version": 1,
  "tool": "greeter",
  "entry": "tools.sample_tool:greet",
  "payload": { "name": "Ada" },
  "sandbox": true,
  "trace_id": "uuid",
  "capability_context": { "guarantees": { "no_network": true } }
}
```

Fields:
- `protocol_version` (number): current protocol version.
- `tool` (string): tool name from the `.ai` declaration.
- `entry` (string): module:function entry point.
- `payload` (object): JSON payload for the tool.
- `sandbox` (boolean, optional): enable sandboxed execution.
- `trace_id` (string, optional): trace correlation id.
- `capability_context` (object, optional): guarantees + sources for enforcement.

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
  "error": { "type": "ValueError", "message": "Missing input", "reason_code": "guarantee_blocked" }
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

## Service capability handshake (HTTP)

Request (POST `/capabilities/handshake`):
```json
{
  "protocol_version": 1,
  "tool_name": "greeter",
  "runner": "service",
  "required_guarantees": { "no_network": true }
}
```

Response:
```json
{
  "ok": true,
  "enforcement": "enforced",
  "supported_guarantees": { "no_network": true },
  "service_version": "1.0.0"
}
```

## Pack runners
Bundled packs reference runners via `tools.yaml` or `entrypoints` in `pack.yaml`.
Runner selection (`local`, `service`, `container`) is resolved at load time and
surfaced in tool call traces.

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
- local sandbox: `sandbox`
- service handshake: `service_handshake`, `enforcement_level`
- container enforcement: `container_enforcement`
- unsafe overrides: `unsafe_override`
