# Execution How

Explainable execution shows how a flow ran and what did not happen.
It is deterministic and based only on runtime facts.
It never includes AI chain-of-thought.

## Quick use
Run a flow, then ask how it ran:
```bash
n3 run app.ai
n3 how
```

## What it includes
- The ordered steps that ran.
- Why a branch or case was taken.
- Why other branches or cases were skipped.
- Loop counts (repeat and for each).
- Where return happened.
- Where an error happened (if any).

## What it does not include
- AI reasoning or hidden prompts.
- Tool output details beyond the fact of a call.
- Non-deterministic data like timing or randomness.

## Artifacts
Artifacts are managed by namel3ss. Use `n3 status` for the last run summary,
`n3 explain` for failures, and `n3 clean` to remove runtime artifacts.

## See also
- [Engine model (runtime)](runtime.md) — execution model and flow execution.
- [Concurrency](concurrency.md) — parallel execution and traces.
