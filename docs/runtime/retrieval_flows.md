# Retrieval tuning flows

Namel3ss supports four built-in retrieval tuning flows:

- `set_semantic_k(k: int)`
- `set_lexical_k(k: int)`
- `set_final_top_k(k: int)`
- `set_semantic_weight(weight: float)`

## Behavior

- Calls are applied in declaration order within a flow.
- `set_semantic_k` and `set_lexical_k` define candidate pool limits.
- `set_final_top_k` limits final output size after semantic/lexical merge.
- `set_semantic_weight` sets blend weight in `[0, 1]` and defaults to `0.5` when omitted.

## Validation

- Compile-time validation checks ordering and literal argument ranges when literals are provided.
- Runtime raises `ValueError` for out-of-range dynamic values.
- Unsupported tuning-like names raise `UnknownFlowError` at compile time.

## State contract

Runtime stores tuning state under:

`state.retrieval.tuning`

Canonical field order:

1. `semantic_k`
2. `lexical_k`
3. `final_top_k`
4. `semantic_weight`
