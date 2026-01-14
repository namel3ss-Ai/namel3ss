# Memory Explanations

Memory can explain its behavior in plain English.
Explanations are deterministic and rule based.
They are built from the proof pack recorded by memory recall or write.

## CLI usage
Run a recall to capture a proof pack, then ask why:
```bash
n3 memory "hello"
n3 memory why
n3 memory show
n3 memory why --json
```

Outputs are managed by namel3ss and reprinted via the CLI (`n3 memory show`, `n3 memory why`).
For run-level diagnostics use `n3 status` / `n3 explain`; use `n3 clean` to remove runtime artifacts.

## Explanation graph
The explain engine builds a small causal graph from facts already in the proof pack:
- Nodes: recall or write, items, phase, cache, budget, decisions, skips
- Edges: `because` or `skipped_because`

The graph is deterministic with stable ids and ordering.

## Why not
If the proof pack has explicit skip or deny events, the "Why not" section lists them.
If none are recorded, it prints:
"No explicit skip reasons were recorded for this run."

## Studio and traces
Studio traces still show raw memory events.
The CLI explanation uses the same facts and does not invent new ones.
