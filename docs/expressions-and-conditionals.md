# Expressions & Conditionals

Expressions are evaluated deterministically inside flows. Numbers use decimals, booleans are explicit, and list operations are pure and ordered.

## Operators and precedence
Highest to lowest:
- Exponentiation `**` (right-associative)
- Unary `+` and `-`
- `*` `/` `%`
- `+` `-`
- Comparisons (`is greater than`, `is less than`, `is at least`, `is at most`, `is between`, `is strictly between`)
- `not`
- `and`
- `or`

Note: `-2 ** 2` parses as `-(2 ** 2)`.

## Examples (keep it small)

1) let: block
```
flow "demo":
  let:
    a is 10
    b is 5
    c is a + b
```

2) calc: block (formula style)
```
flow "demo":
  calc:
    total = 2 * 3
    state.total = total
```

3) List aggregations (empty lists error)
```
flow "demo":
  let numbers is list:
    1
    2
  let total is sum(numbers)
```

4) map/filter/reduce (pure, ordered)
```
flow "demo":
  let numbers is list:
    1
    2
    3
  let doubled is map numbers with item as n:
    n * 2
  let big is filter doubled with item as x:
    x is greater than 3
  let total is reduce big with acc as s and item as v starting 0:
    s + v
```

5) between / strictly between
```
flow "demo":
  if value is between 1 and 10:
    return true
  if value is strictly between 1 and 10:
    return true
```

## Composite example
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
