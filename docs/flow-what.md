# Run Outcome (What)

`n3 what` shows a deterministic run outcome based on recorded runtime facts.
It is calm, short, and does not guess why something happened.

## Quick use
Run a flow, then read the outcome:
```bash
n3 run app.ai
n3 what
```

## What it includes
- Status (ok/partial/error).
- Store begin/commit/rollback results.
- State save attempts and results.
- Memory persistence attempts and results.
- A factual list of what did not happen.

## What it does not include
- Timings or durations.
- Inferred causes beyond recorded facts.

## Artifacts
Artifacts are managed by namel3ss. Use `n3 status` for the last run summary,
`n3 explain` for failures, and `n3 clean` to remove runtime artifacts.
