# Errors Fix

Explainable errors show what went wrong, the impact, and recovery options.
Output is deterministic and based only on runtime facts.
It never auto-fixes anything or guesses recovery.

## Quick use
Run a flow, then ask for the fix report:
```bash
n3 run app.ai
n3 fix
```

## What it includes
- Error summary (what, kind, where).
- Impact from execution, tools, flow, and ui artifacts.
- Recovery options inferred from explicit denial reasons.

## What it does not include
- Automatic fixes.
- AI-generated recovery steps.
- Guessed root causes without evidence.

## Artifacts
After a run, the runtime saves:
- `.namel3ss/errors/last.json`
- `.namel3ss/errors/last.plain`

The `n3 fix` command writes:
- `.namel3ss/errors/last.fix.txt`
