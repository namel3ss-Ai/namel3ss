# CLI: what

`n3 what` shows the last run outcome in a deterministic, inspectable format.

## What it is
- A stable outcome contract written after each flow run.
- A calm, short summary of store/state/memory actions.

## What it includes
- Status (ok/partial/error).
- Store begin/commit/rollback results.
- State save attempts and results.
- Memory persistence attempts and results.
- A factual list of what did not happen.

## What it does NOT include
- Timings or durations.
- Inferred causes beyond recorded facts.

## Artifacts
Artifacts are managed by namel3ss. Use `n3 status` for the last run summary,
`n3 explain` for failures, and `n3 clean` to remove runtime artifacts.
