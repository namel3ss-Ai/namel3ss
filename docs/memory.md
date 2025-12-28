# Memory (Contract v1 + Governance)

Phase 4 keeps the Phase 0 contract intact while adding memory phases, diffs, and deterministic deletion.

## Memory kinds
- `short_term`: recent conversation turns (user/ai messages).
- `semantic`: snippets from prior interactions, scored deterministically.
- `profile`: stable facts about a session/user.

## MemoryItem fields
Core fields remain unchanged:
- `id` (string): deterministic, derived from `(session, kind, sequence_no)`.
- `kind` (string): one of `short_term`, `semantic`, `profile`.
- `text` (string): primary payload.
- `source` (string): `user`, `ai`, `tool`, or `system`.
- `created_at` (int): monotonic counter (deterministic).
- `importance` (number): rule-based, deterministic.
- `scope` (string): "session" in Phase 0 (still `session` in Phase 4).
- `meta` (dict): optional metadata (defaults to `{}`).

Phase 2 extends `meta` with optional fields, and Phase 4 adds phase metadata:
- `meta.event_type`: `preference`, `decision`, `fact`, `correction`, `execution`, `context`.
- `meta.importance_reason`: list of deterministic rules that set importance.
- `meta.recall_reason`: list of recall reasons (`matches_query`, `recency`, `importance`, `active_rule`).
- `meta.space`: `session | user | project | system`.
- `meta.owner`: stable owner id for the space.
- `meta.summary_of`: list of summarized item ids (for short-term summaries).
- `meta.dedup_key`: stable key for conflicts/dedupe (`event_type + normalized text`, or `fact:<key>`).
- `meta.score`: semantic recall score (combined hybrid score).
- `meta.key`: fact key for profile memory.
- `meta.source_turn_ids`: ids of turns that produced a profile fact.
- `meta.authority`: `user_asserted`, `ai_inferred`, `tool_verified`, `system_imposed`.
- `meta.authority_reason`: short explanation of the authority source.
- `meta.promoted_from`: id of the source item when promoted across spaces.
- `meta.promotion_reason`: stable promotion reason code.
- `meta.policy_tags`: applied policy tags (e.g., `allowed_by:write_policy:normal`, `kept_by:retention_rule`).
- `meta.expires_at`: deterministic tick when TTL expires (if applicable).
- `meta.phase_id`: deterministic phase id (`phase-1`, `phase-2`, ...).
- `meta.phase_name`: optional human label for the phase.
- `meta.phase_started_at`: deterministic counter when the phase started.
- `meta.phase_reason`: stable reason code for the phase start.

## Memory policy contract
Policies are enforced (not advisory) and are emitted in traces under `policy`.
See `docs/memory-policy.md` for the full policy contract and examples.

Key fields:
- `write_policy`: `none | minimal | normal | aggressive`.
- `allow_event_types` / `deny_event_types`: explicit allow/deny lists.
- `retention`: per kind + event type rules (`never | ttl | decay`, with deterministic ticks).
- `promotion`: which event types can be written to `semantic`/`profile`.
- `spaces`: read order + write spaces + promotion rules between spaces.
- `phase`: phase settings (`enabled`, `mode`, `allow_cross_phase_recall`, `max_phases`, `diff_enabled`).
- `privacy`: deny patterns + allowlisted profile keys.
- `authority_order`: ordered list for conflict resolution.

Defaults are deterministic and derived from Phase 1 settings (`write_policy`, `forget_policy`).

## Authority + conflict resolution
Authority levels (highest first):
- `system_imposed` > `tool_verified` > `user_asserted` > `ai_inferred`

Conflict resolution (deterministic):
1) authority
2) correction
3) recency
4) importance

Correction events with `user_asserted` authority (or higher) can override higher-authority items.
Losers are deleted immediately and emit `memory_deleted` with reason `superseded`.

## Retention + forgetting
Retention is deterministic and counter-based:
- `ttl`: expire at `created_at + ttl_ticks`.
- `decay`: expire after `ttl_ticks` of age.

Expired items emit `memory_forget` with reason `ttl_expired` or `decay`.
Short-term window evictions emit `memory_forget` with reason `decay` (deterministic turn window).
All expired items are also deleted and emit `memory_deleted` with reason `expired`.

## Privacy rules
Privacy rules are enforced before writes:
- obvious secrets/tokens are denied
- profile facts are allowlisted by key

Denied writes emit `memory_denied` with a stable reason code.

## Trace events
Memory emits canonical events per AI call. Governance and phase events extend traces while keeping Phase 0 keys intact.

### `memory_recall`
Required keys:
- `type`: `memory_recall`
- `ai_profile`
- `session`
- `query` (redacted + truncated)
- `recalled`: MemoryItem-like dicts (include `meta.recall_reason` + optional `meta.policy_tags`)
- `policy`: expanded policy snapshot (includes retention, promotion, privacy, authority order)
- `deterministic_hash`: hash of recalled `(kind, id)` in order
- `spaces_consulted`: ordered list of spaces consulted
- `recall_counts`: per-space recall counts
- `current_phase`: current phase metadata (`phase_id`, `phase_name`, `phase_started_at`, `phase_reason`)
- `phase_counts`: per-space per-phase recall counts (optional)

### `memory_write`
Required keys:
- `type`: `memory_write`
- `ai_profile`
- `session`
- `written`: MemoryItem-like dicts (include `meta.event_type` + `meta.importance_reason` + `meta.authority`)
- `reason`: `interaction_recorded`

### `memory_denied`
Required keys:
- `type`: `memory_denied`
- `ai_profile`
- `session`
- `attempted`: MemoryItem-like dict (redacted)
- `reason`: stable denial code (e.g., `write_policy_none`, `privacy_deny_sensitive`)
- `policy_snapshot`

### `memory_conflict`
Required keys:
- `type`: `memory_conflict`
- `ai_profile`
- `session`
- `winner_id`, `loser_id`
- `rule`: `authority | correction | recency | importance`
- `dedup_key`

### `memory_forget`
Required keys:
- `type`: `memory_forget`
- `ai_profile`
- `session`
- `memory_id`
- `reason`: `ttl_expired | decay`
- `policy_snapshot`

### `memory_border_check`
Required keys:
- `type`: `memory_border_check`
- `ai_profile`
- `session`
- `action`: `read | write | promote`
- `from_space` (and `to_space` for write/promote)
- `allowed`: true/false
- `reason`: stable code
- `policy_snapshot`

### `memory_promoted`
Required keys:
- `type`: `memory_promoted`
- `ai_profile`
- `session`
- `from_space`, `to_space`
- `from_id`, `to_id`
- `authority_used`
- `reason`
- `policy_snapshot`

### `memory_promotion_denied`
Required keys:
- `type`: `memory_promotion_denied`
- `ai_profile`
- `session`
- `from_space`, `to_space`
- `memory_id`
- `allowed`: false
- `reason`
- `policy_snapshot`

### `memory_phase_started`
Required keys:
- `type`: `memory_phase_started`
- `ai_profile`
- `session`
- `space`
- `owner`
- `phase_id`
- `reason`
- `policy_snapshot`

### `memory_deleted`
Required keys:
- `type`: `memory_deleted`
- `ai_profile`
- `session`
- `space`
- `owner`
- `phase_id`
- `memory_id`
- `reason`
- `policy_snapshot`

### `memory_phase_diff`
Required keys:
- `type`: `memory_phase_diff`
- `ai_profile`
- `session`
- `space`
- `owner`
- `from_phase_id`, `to_phase_id`
- `added_count`, `deleted_count`, `replaced_count`
- `top_changes`

Redaction: trace payloads use the same redaction rules as other traces.

## Studio (Plain view)
Memory traces can be inspected in Studio with a bracketless Plain view:
- one key per line (`key: value`)
- nested keys use dot notation (`policy.short_term`)
- lists use indexed keys (`recalled.count`, `recalled.1.id`)

## Testing approach
- Unit tests enforce policy evaluation, authority, and conflict resolution.
- Golden fixtures lock governance trace events.
- Retention/decay is tested with deterministic counters.
- Regression tests verify AI outputs remain unchanged while traces add governance events.

See `docs/memory-spaces.md` and `docs/memory-phases.md` for space/border/promotion and phase specifics.
- `summary_lines`
