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
- `lane` my, team, system
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

## Memory lanes
- My lane holds personal memory for the current user
- Team lane holds shared memory for the project
- System lane holds system rules and is read only
- Team lane writes are only allowed by explicit promotion
- Team lane writes create proposals that must be approved

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

## Testing approach
- Unit tests enforce policy evaluation and conflict rules
- Golden fixtures lock trace event shapes
- Retention and decay use deterministic counters
- Regression tests verify AI outputs remain unchanged

See the memory docs for policy, phases, agreements, trust, explanations, connections, impact, and lanes.
