# Trace Schema v1

Trace schema v1 freezes required keys for tool call traces.
The canonical version map lives at resources/spec_versions.json under trace_schema.

## Tool call traces v1
Every tool call trace includes:
- type tool_call
- tool_name
- resolved_source builtin_pack installed_pack binding
- runner local service container
- status ok error
- duration_ms
- timeout_ms
- protocol_version

### Pack tools
When the tool resolves from a pack, include:
- pack_id
- pack_version

### Binding tools
When the tool resolves from an app binding, include:
- entry

### Runner specific keys
For runner local:
- python_env
- python_path
- deps_source

For runner service:
- service_url

For runner container:
- container_runtime
- image
- command

## AI call traces
AI call traces are versioned separately by TRACE_VERSION.
Memory trace events are part of the AI trace stream.
They are defined in docs/memory.md and docs/memory-policy.md.

Memory events include:
- memory_recall
- memory_write
- memory_denied
- memory_conflict
- memory_forget
- memory_border_check
- memory_promoted
- memory_promotion_denied
- memory_phase_started
- memory_budget
- memory_compaction
- memory_cache_hit
- memory_cache_miss
- memory_wake_up_report
- memory_restore_failed
- memory_pack_loaded
- memory_pack_merged
- memory_pack_overrides
- memory_deleted
- memory_phase_diff
- memory_team_summary
- memory_proposed
- memory_approved
- memory_rejected
- memory_agreement_summary
- memory_trust_check
- memory_approval_recorded
- memory_trust_rules
- memory_rule_applied
- memory_rules_snapshot
- memory_rule_changed
- memory_handoff_created
- memory_handoff_applied
- memory_handoff_rejected
- memory_agent_briefing
- memory_explanation
- memory_links
- memory_path
- memory_impact
- memory_change_preview

### Memory budget and cache events
Memory budget events include type, space, lane, phase_id, owner, title, and lines.
Memory compaction events include action, items_removed_count, summary_written, reason, title, and lines.
Memory cache events include type, space, lane, phase_id, title, and lines.

### Memory restore events
Memory wake up report events include type, project_id, title, and lines.
Memory restore failed events include type, project_id, title, and lines.

### Memory pack events
Memory pack loaded events include type, pack_id, pack_version, title, and lines.
Memory pack merged events include type, title, and lines with pack ids in order.
Memory pack overrides events include type, title, and override lines.

## Capability check traces v1
Every denied capability check must include:
- type capability_check
- tool_name
- resolved_source builtin_pack installed_pack binding
- runner local service container
- capability filesystem_write, filesystem_read, network, subprocess, env_read, env_write, secrets
- allowed true or false
- guarantee_source tool, pack, user, policy
- reason stable code such as guarantee_blocked, coverage_missing, secrets_allowed, secrets_blocked
- protocol_version

Optional:
- duration_ms
