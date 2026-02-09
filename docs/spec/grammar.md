# Grammar Specification

## Frozen Surface
For `namel3ss-spec@1`, grammar behavior is frozen.

The parser grammar authority is:
- `spec/grammar/namel3ss.grammar`
- `src/namel3ss/parser/generated/grammar_snapshot.py`

`docs/grammar/current.md` is a human-readable snapshot and **must** align with parser behavior.

## Rules
- Grammar changes are breaking by default.
- Grammar changes **must** include explicit breaking-change acknowledgment in CI.
- Grammar snapshot drift **must** fail CI.
- Grammar updates **must** include migration guidance.

## Determinism
- Parse acceptance/rejection for the same source text **must** be deterministic.
- Grammar snapshots **must** be stable and hashable.
