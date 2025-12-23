# Expressions & Conditionals

Expressions are evaluated deterministically inside flows. Numbers support decimals and arithmetic.

## Examples (keep it small)

1) Decimal literals
```
flow "demo":
  let price is 10.50
  return price
```

2) Arithmetic + precedence
```
flow "demo":
  let total is 2 + 3 * 4
  return total
```

3) Parentheses
```
flow "demo":
  let total is (2 + 3) * 4
  return total
```

4) Comparisons
```
flow "demo":
  if total is at least 100:
    return "discount"
  else:
    return "standard"
```

5) Use state values
```
flow "compute_total":
  let base is state.order.price * state.order.quantity
  return base
```

Note: decimal results are preserved exactly; CLI JSON output may serialize non-integer decimals as strings to avoid rounding.
