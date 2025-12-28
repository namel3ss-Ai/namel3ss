# Trace Schema v1

Trace schema v1 freezes the required keys for tool call traces. The canonical
version map lives at `resources/spec_versions.json` (`trace_schema`: v1).

## Tool call traces (v1)

Every tool call trace must include:
- `type` (`tool_call`)
- `tool_name`
- `resolved_source` (`builtin_pack`, `installed_pack`, `binding`)
- `runner` (`local`, `service`, `container`)
- `status` (`ok`, `error`)
- `duration_ms`
- `timeout_ms`
- `protocol_version`

### Pack tools
When the tool resolves from a pack, traces must also include:
- `pack_id`
- `pack_version`

### Binding tools
When the tool resolves from an app binding, traces must also include:
- `entry`

### Runner-specific keys
- `runner = local`
  - `python_env`
  - `python_path`
  - `deps_source`
- `runner = service`
  - `service_url`
- `runner = container`
  - `container_runtime`
  - `image`
  - `command`

## AI call traces
AI call traces are versioned separately by `TRACE_VERSION` and may evolve.
When frozen, they will receive a dedicated version key.
Memory trace events (`memory_recall`, `memory_write`, `memory_denied`, `memory_conflict`, `memory_forget`,
`memory_border_check`, `memory_promoted`, `memory_promotion_denied`, `memory_phase_started`,
`memory_deleted`, `memory_phase_diff`)
are part of the AI trace stream and are defined in `docs/memory.md` and `docs/memory-policy.md`.

## Capability check traces (v1)

Every denied capability check must emit:
- `type` (`capability_check`)
- `tool_name`
- `resolved_source` (`builtin_pack`, `installed_pack`, `binding`)
- `runner` (`local`, `service`, `container`)
- `capability` (`filesystem_write`, `filesystem_read`, `network`, `subprocess`, `env_read`, `env_write`, `secrets`)
- `allowed` (`true` or `false`)
- `guarantee_source` (`tool`, `pack`, `user`, `policy`)
- `reason` (stable code such as `guarantee_blocked`, `coverage_missing`, `secrets_allowed`, `secrets_blocked`)
- `protocol_version`

Optional:
- `duration_ms`
