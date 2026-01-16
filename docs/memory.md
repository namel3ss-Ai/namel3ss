# Memory Contract v1 and Governance

Memory is deterministic, policy driven, and inspectable.
This doc describes the memory contract and trace events.

## Memory kinds
- `short_term` stores recent conversation turns
- `semantic` stores recallable snippets
- `profile` stores stable facts

## MemoryItem fields
- `id` deterministic string
- `kind` one of `short_term`, `semantic`, `profile`
- `text` string payload
- `source` user, ai, tool, or system
- `created_at` monotonic counter
- `importance` number
- `scope` session
- `meta` optional map

## Meta fields
- `event_type` preference, decision, fact, correction, execution, rule, context
- `importance_reason` list of rules
- `recall_reason` list of recall reasons
- `space` session, user, project, system
- `owner` stable owner id
- `lane` my, team, system, agent
- `agent_id` agent id for agent lane items
- `visible_to` me, team, all
- `can_change` true or false
- `agreement_status` pending, approved, rejected
- `proposal_id` stable id for team agreements
- `summary_of` list of memory ids
- `dedup_key` stable key for dedupe
- `score` semantic score
- `key` profile fact key
- `source_turn_ids` ids that produced a fact
- `authority` user_asserted, ai_inferred, tool_verified, system_imposed
- `authority_reason` short text
- `promoted_from` id of the source item
- `promotion_reason` stable code
- `policy_tags` applied policy tags
- `expires_at` deterministic tick
- `phase_id` phase id
- `phase_name` optional label
- `phase_started_at` deterministic counter
- `phase_reason` stable reason code
- `links` list of link records
- `link_preview_text` map of id to preview
- `handoff_packet_id` handoff packet id
- `handoff_from_agent` agent id that sent the handoff
- `handoff_to_agent` agent id that received the handoff
- `handoff_link_previews` list of preview lines

## Memory lanes
- My lane holds personal memory for the current user
- Agent lane holds private memory for one agent
- Team lane holds shared memory for the project
- System lane holds system rules and is read only
- Team lane writes are only allowed by explicit promotion
- Team lane writes create proposals that must be approved
Agent lanes do not share memory without a handoff.

## Governed agent memory (facts)
Agent memory is explicit and traceable:
- Agent steps write memory only through recorded `memory_write` events.
- Explain/Studio surfaces a memory facts summary (keys, counts, last_updated_step) without raw values.
- Snapshots live under `.namel3ss/memory` and use deterministic counters (no wall-clock timestamps).

## Memory policy contract
Policies are enforced and recorded under `policy` in traces.

Key fields:
- `write_policy` none, minimal, normal, aggressive
- `allow_event_types` and `deny_event_types`
- `retention` per kind and event type
- `promotion` rules for semantic and profile
- `spaces` read order, write spaces, promotion rules
- `lanes` read order, write lanes, team rules
- `trust` propose, approve, reject levels and approval count
- `phase` enabled, mode, allow_cross_phase_recall, max_phases, diff_enabled
- `privacy` deny patterns and allowlisted profile keys
- `authority_order` overwrite order

## Memory budgets
Budgets keep memory fast and small.
Budgets apply per space, lane, and phase.
Soft limit actions use compaction, low value removal, or deny write.
See docs/memory-budgets.md for details.

## Memory packs
Memory packs reuse trust, agreement defaults, budgets, lane defaults, phase defaults, and rules.
Packs load from packs memory under the project root.
Local overrides live under dot namel3ss.
Rules append in pack order.
Duplicate rules keep the last source.
Studio shows pack summary and overrides.
See docs/memory-packs.md for details.

## Memory persistence
Memory is saved to disk in the project folder.
Restore loads the exact memory state or fails fast.
A wake up report trace appears after restore or fresh start.
See docs/memory-persist.md for details.

## Memory CLI and proof packs
Memory recall and explain are available through a single command:
- `n3 memory "hello"`
- `n3 memory why`
- `n3 memory show`
- `n3 memory @assistant "hello"`

The memory CLI writes deterministic artifacts managed by namel3ss.
Use `n3 memory show` / `n3 memory why` to review them,
`n3 status` / `n3 explain` for run diagnostics, and `n3 clean` to remove runtime artifacts.

## Memory proof harness
Deterministic scenarios live under `tests/memory_proof/scenarios`.
Goldens live under `tests/memory_proof/golden`.
Run output is written under `tests/memory_proof/output`.

Generate or refresh goldens:
```bash
python3 tools/memory_proof_generate.py
```

Check against goldens (CI):
```bash
python3 tools/memory_proof_check.py
```

See docs/memory-proof.md for details.

## Trace events
Memory emits canonical events on every AI call.

### `memory_recall`
- `type` memory_recall
- `ai_profile`
- `session`
- `query` redacted text
- `recalled` list of MemoryItem like dicts
- `policy` snapshot
- `deterministic_hash`
- `spaces_consulted`
- `recall_counts`
- `current_phase`
- `phase_counts` optional

### `memory_write`
- `type` memory_write
- `ai_profile`
- `session`
- `written` list of MemoryItem like dicts
- `reason` interaction_recorded

### Governance and phase events
- `memory_denied`
- `memory_conflict`
- `memory_forget`
- `memory_border_check`
- `memory_promoted`
- `memory_promotion_denied`
- `memory_budget`
- `memory_compaction`
- `memory_cache_hit`
- `memory_cache_miss`
- `memory_phase_started`
- `memory_deleted`
- `memory_phase_diff`
- `memory_team_summary`
- `memory_proposed`
- `memory_approved`
- `memory_rejected`
- `memory_agreement_summary`
- `memory_trust_check`
- `memory_approval_recorded`
- `memory_trust_rules`
- `memory_rule_applied`
- `memory_rules_snapshot`
- `memory_rule_changed`
- `memory_handoff_created`
- `memory_handoff_applied`
- `memory_handoff_rejected`
- `memory_agent_briefing`

### Persistence events
- `memory_wake_up_report`
- `memory_restore_failed`

### Pack events
- `memory_pack_loaded`
- `memory_pack_merged`
- `memory_pack_overrides`

### Explanation and links
- `memory_explanation`
- `memory_links`
- `memory_path`
- `memory_impact`
- `memory_change_preview`

## Plain view in Studio
Studio shows a bracketless Plain view for memory traces.
Each line uses key: value with dot notation for nested fields.
Lists use count and indexed keys.
Studio also shows a Memory budget section in the Traces panel.

## Testing approach
- Unit tests enforce policy evaluation and conflict rules
- Golden fixtures lock trace event shapes
- Retention and decay use deterministic counters
- Regression tests verify AI outputs remain unchanged

## Reference
- [Memory policy](memory-policy.md)
- [Memory lanes](memory-lanes.md)
- [Memory agreement](memory-agreement.md)
- [Memory spaces](memory-spaces.md)
- [Memory phases](memory-phases.md)
- [Memory trust](memory-trust.md)
- [Memory rules](memory-rules.md)
- [Memory handoff](memory-handoff.md)
- [Memory budgets](memory-budgets.md)
- [Memory persistence](memory-persist.md)
- [Memory packs](memory-packs.md)
- [Memory explanations](memory-explanations.md)
- [Memory proof harness](memory-proof.md)
- [Memory connections](memory-connections.md)
- [Memory impact](memory-impact.md)

## Capability ids
runtime.memory
runtime.memory_packs
