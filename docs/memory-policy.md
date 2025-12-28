# Memory Governance Policy

Phase 4 uses a governed memory policy that is enforced on every write and exposed via traces.

## Policy contract
Policies are deterministic and serializable. The default contract is emitted under `policy` in `memory_recall` traces.

Key fields:
- `write_policy`: `none | minimal | normal | aggressive`
- `allow_event_types`: explicit allowlist (empty = allow all)
- `deny_event_types`: explicit denylist
- `retention`: per kind + event type (`never | ttl | decay`)
- `promotion`: allowed event types for `semantic` / `profile`
- `spaces`: read order + write spaces + promotion rules between spaces
- `phase`: phase settings (`enabled`, `mode`, `allow_cross_phase_recall`, `max_phases`, `diff_enabled`)
- `privacy`: deny patterns + allowlisted profile keys
- `authority_order`: overwrite hierarchy

## Authority
Authority controls overwrites:
- `system_imposed` > `tool_verified` > `user_asserted` > `ai_inferred`

Authority is stored on each MemoryItem (`meta.authority`, `meta.authority_reason`).

## Conflict resolution
Conflicts are detected by `meta.dedup_key` or profile fact key.
Resolution is deterministic:
1) authority
2) correction
3) recency
4) importance

Losers are deleted immediately and emit `memory_deleted` with reason `superseded`.

## Retention + forgetting
Retention is deterministic and counter-based:
- `ttl`: expire at `created_at + ttl_ticks`
- `decay`: expire after `ttl_ticks` of age

When items expire, a `memory_forget` event is emitted with a stable reason code:
- `ttl_expired`
- `decay`

Expired, superseded, or promoted items also emit `memory_deleted`.

## Privacy + deny rules
Privacy rules are enforced before writes:
- deny obvious secrets/tokens
- allowlist profile keys

Denied writes emit `memory_denied` with:
- `attempted` (redacted)
- `reason` (stable code)
- `policy_snapshot`

## Trace events
Governance trace events:
- `memory_denied`: policy or privacy blocked a write
- `memory_conflict`: deterministic winner/loser selected
- `memory_forget`: TTL/decay removal
- `memory_border_check`: read/write/promote border decision
- `memory_promoted`: successful cross-space promotion
- `memory_promotion_denied`: promotion blocked by policy/authority
- `memory_phase_started`: phase timeline marker
- `memory_deleted`: explicit deletion trace
- `memory_phase_diff`: phase-to-phase diff summary

## Determinism
- `created_at` is a monotonic counter
- `id` is deterministic per session + kind
- ordering is stable and replayable

## Testing
- Unit tests cover policy evaluation and conflict resolution
- Golden fixtures lock governance trace schemas
- Retention/decay uses deterministic counters for repeatable tests
