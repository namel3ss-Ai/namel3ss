# CLI: fix

`n3 fix` shows the last runtime failure in a deterministic, inspectable format.

## What it is
- A stable error contract written when a run fails.
- A calm, short error summary you can re-print later.

## What it includes
- Error id, boundary, and kind.
- What happened, why, and how to fix.
- Where it happened (flow, statement, line/column when known).

## What it does NOT include
- A Python traceback.
- Inferred causes beyond the exception and runtime context.

## Artifacts
Artifacts are managed by namel3ss. Use `n3 explain` for a calm failure summary,
`n3 status` for the last run overview, and `n3 clean` to remove runtime artifacts.
