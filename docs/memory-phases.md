# Memory Phases

Phase 4 turns memory into a deterministic timeline. A **phase** is a stable period
of memory where the current items reflect “what we believe now.”

## What a phase is
- A phase is a monotonic, deterministic counter per space/owner.
- Phase ids use English-first naming: `phase-1`, `phase-2`, ...
- No wall-clock time is used.

## When phases start
Default behavior:
- Phase 1 is created automatically at the first memory write for a space/owner.

Manual phase start (internal API):
- Set `state._memory_phase_token` to a new string before an AI call.
- Optional: set `state._memory_phase_name` and `state._memory_phase_reason`.
- A new phase starts the next time memory is used.

## Phase-aware recall
By default, recall uses **current phase only**.
If `policy.phase.allow_cross_phase_recall` is enabled, recall consults current phase
first, then older phases in descending order.

## Budgets and cache
Budgets are tracked per phase and lane.
Compaction keeps a summary item in the same phase.
Recall cache keys include the phase id.

## Persistence
Phase data is saved with the memory snapshot.
Restore keeps phase ids and diff order stable.
Wake up report confirms what was loaded.

## Phase diff
Phase diff compares two phases within a space/owner and reports:
- added items
- deleted items
- replaced items (same fact key, new active id)

Manual diff request (internal API):
- Set `state._memory_phase_diff_from` and `state._memory_phase_diff_to`.
- Optional: set `state._memory_phase_diff_space` (defaults to `session`).
- The next AI call emits `memory_phase_diff`.

## Deletion with traceability
When a memory item is replaced, promoted, expired, or a conflict loser:
- the old item is **deleted from storage**
- a `memory_deleted` trace is emitted with a stable reason code

This keeps memory clean while preserving explainability in traces.

## Trace events
Phase-related trace events:
- `memory_phase_started`
- `memory_deleted`
- `memory_phase_diff`

See `docs/memory.md` and `docs/memory-policy.md` for full schema details.
