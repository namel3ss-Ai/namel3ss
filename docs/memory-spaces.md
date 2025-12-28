# Memory Spaces

Phase 3 adds explicit memory spaces with strict borders and promotion.

## Spaces + owners
Each MemoryItem lives in exactly one space (`meta.space`) with a stable owner (`meta.owner`):
- `session`: per-session context, owner = session id (or `anonymous`).
- `user`: per-user memory, owner = user id (or `anonymous`).
- `project`: shared project memory, owner = deterministic project id.
- `system`: global memory, owner = `system`.

Project ids are deterministic hashes derived from `project_root` (or `app.ai` path).
Each space maintains its own phase timeline (`phase-1`, `phase-2`, ...).

## Borders
Borders are enforced (not advisory):
- Reads follow a policy-driven order (default: `session → user → project → system`).
- Writes default to `session` only.
- Cross-space writes require an explicit promotion decision.

Every read/write/promote decision emits `memory_border_check`.

## Promotion
Promotion is explicit and traceable:
- Triggered by deterministic requests (e.g., “remember this for me/project”).
- Allowed paths (default):
  - `session → user` (authority ≥ `user_asserted`, event type allowlist).
  - `session → project` (authority ≥ `tool_verified`, or explicit decision).
  - `user → project` (authority ≥ `user_asserted`).
  - `project → system` is disallowed by default.

On success, a new item is written in the target space with:
- `meta.promoted_from`
- `meta.promotion_reason`

On deny, `memory_promotion_denied` is emitted with a stable reason code.

## Recall routing
- Spaces are consulted in a deterministic order.
- Items are ordered by space priority, then deterministic in-space ordering.
- Each recalled item includes `meta.recall_reason` + `space:<space>`.

## Trace events
New space/governance events:
- `memory_border_check`: read/write/promote decision + policy snapshot.
- `memory_promoted`: successful promotion (`from_space`, `to_space`, ids, authority).
- `memory_promotion_denied`: promotion blocked (reason + policy snapshot).

## Determinism
- Store keys are `space:owner`.
- IDs are deterministic per store key and kind.
- Recall ordering is stable and replayable.
