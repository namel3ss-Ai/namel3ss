# Memory Governance Policy

This policy is enforced on every write and recorded in traces.

## Policy contract
Policies are deterministic and serializable.
The contract is emitted under `policy` in `memory_recall` traces.

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

## Authority
Authority controls overwrites in conflicts.
Order from highest to lowest:
- system_imposed
- tool_verified
- user_asserted
- ai_inferred

## Conflict resolution
Conflicts are detected by `meta.dedup_key` or profile fact key.
Resolution is deterministic.
Order is authority then correction then recency then importance.
Losers are deleted and emit `memory_deleted` with reason conflict_loser.

## Retention and forgetting
Retention is deterministic and counter based.
- ttl expires at created_at plus ttl_ticks
- decay expires after ttl_ticks of age

Expired items emit `memory_forget` with reason ttl_expired or decay.
Expired, replaced, or promoted items emit `memory_deleted`.

## Privacy and deny rules
Privacy rules are enforced before writes.
Sensitive patterns are denied.
Profile facts are allowlisted by key.
Denied writes emit `memory_denied` with a stable reason.

## Lanes and borders
Lane rules are enforced for reads and writes.
My lane reads are always allowed for the current user.
Team lane reads follow policy and border checks.
System lane is read only for normal flows.
Border checks emit `memory_border_check` with space and lane details.
Team lane writes create proposals that require approval.

## Rules
Rules are stored as memory items.
Rules live in the team lane or system lane.
Rules are enforced before proposals and promotions.
Rule decisions emit `memory_rule_applied`.
Rule snapshots emit `memory_rules_snapshot`.
Rule changes emit `memory_rule_changed`.

## Trace events
Governance trace events include:
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
- `memory_rule_applied`
- `memory_rules_snapshot`
- `memory_rule_changed`
- `memory_explanation`
- `memory_links`
- `memory_path`
- `memory_impact`
- `memory_change_preview`

See the memory docs for explanations, links, impact, and lanes.

## Determinism
- created_at is a monotonic counter
- id is deterministic per session and kind
- ordering is stable and replayable

## Testing
- Unit tests cover policy evaluation and conflict resolution
- Golden fixtures lock trace schemas
- Retention uses deterministic counters
