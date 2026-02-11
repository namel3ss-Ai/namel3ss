# Retrieval Trace and What-If

Evolution Edition adds a deterministic retrieval trace contract for Studio diagnostics.

## Capability Gate

Enable:

```ai
capabilities:
  diagnostics.trace
```

If missing, compiler emits:

`Warning: Retrieval trace diagnostics are disabled (missing capability diagnostics.trace).`

## Trace Contract

Trace payload includes:

- `query`
- `params` (`semantic_weight`, `semantic_k`, `lexical_k`, `final_top_k`)
- `filter_tags` (sorted)
- `semantic`, `lexical`, `final` candidate lists
- `tie_breaker` (static deterministic ordering description)

## Deterministic Ordering

Rows are sorted with:

1. `final_score` descending
2. `semantic_score` descending
3. `lexical_score` descending
4. `doc_id` ascending

## What-If Simulation

Studio computes deterministic what-if ranking from stored trace data only:

- No external calls
- No rerun of retrieval
- Pure function of `(trace, params)`
- Same input produces identical output
