# Tools With

Explainable tools show what tools ran, why they were allowed, and why some were blocked.
Output is deterministic and based only on runtime facts.
It never includes AI chain-of-thought.

## Quick use
Run a flow, then ask with:
```bash
n3 run app.ai
n3 with
```

## What it includes
- Tool intent (what was called).
- Permission outcome (allowed or blocked) and capability reasons.
- Effect summary (ok/error, duration, output summary).

## What it does not include
- Tool implementation details.
- Hidden AI reasoning.
- Guessed explanations when data is missing.

## Artifacts
After a run, the runtime saves:
- `.namel3ss/tools/last.json`
- `.namel3ss/tools/last.plain`

The `n3 with` command writes:
- `.namel3ss/tools/last.with.txt`
