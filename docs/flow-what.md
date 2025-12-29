# Flow What

Explainable flows show intent, outcome, why, and what did not happen.
Output is deterministic and based only on runtime facts.
It never includes AI chain-of-thought or guessed intent.

## Quick use
Run a flow, then ask what it did:
```bash
n3 run app.ai
n3 with
n3 what
```

## What it includes
- Flow intent (name, requires, audited, expected effects).
- Outcome status (ok/partial/error) and return summary if available.
- Tool outcome summary (ok/blocked/error counts).
- Memory write summary when available.
- Why lines from branch, match, and loop decisions.
- What did not happen (skipped branches and blocked tools).

## What it does not include
- AI chain-of-thought.
- Guessed intent or hidden prompts.
- Tool implementation details beyond the facts recorded.

## Artifacts
After a run, the runtime saves:
- `.namel3ss/flow/last.json`
- `.namel3ss/flow/last.plain`

The `n3 what` command writes:
- `.namel3ss/flow/last.what.txt`
