# Expression Surface v1

This document describes the code-backed expression surface. The source of truth is:
- `tests/fixtures/expression_surface_v1.ai`
- `tests/contract/test_expression_surface_contract.py`
- `n3 expr-check`

## Scope (v1)
- Operators: `+ - * / % **` (right-associative exponentiation).
- Unary minus binds as `-(2 ** 2)`.
- Comparisons: `is greater than`, `is less than`, `is at least`, `is at most`, `is between`, `is strictly between`.
- List ops: `list length/append/get` and map ops (`map get/set/keys`).
- List aggregations: `sum/min/max/mean/median` with numeric lists only; empty lists raise `math.empty_list`.
- List transforms: `map/filter/reduce` block expressions with scoped binders.
- `let:` blocks for grouped declarations.
- `calc:` blocks for formula assignments; `state.<path> = expr` desugars to `set state.<path> is expr`.

## Not supported
- `=` outside `calc:` blocks.
- Lambdas or implicit function literals.

## Contract example
```
spec is "1.0"
flow "demo":
  let numbers is list:
    1
    2
    3
    10

  calc:
    doubled = map numbers with item as n:
      n * 2
    big = filter doubled with item as x:
      x is greater than 5
    state.total = reduce big with acc as s and item as v starting 0:
      s + v
    state.avg = mean(big)
    d = 2 ** 3 ** 2
    ok = state.total is between 0 and 100

  return map:
    "total" is state.total
    "avg" is state.avg
    "d" is d
    "ok" is ok
```

## Guardrails
- `n3 expr-check` runs the expression surface contract tests and emits a deterministic JSON report.
- CI and release gates run `expr-check` and fail on regressions.
