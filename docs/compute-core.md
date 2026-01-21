# Compute Core Phase 2

This document describes the minimal compute core.
It is designed to stay deterministic and easy to read.

## Define function

Use define function to declare a function.

Example

```
define function "apply tax":
  input:
    subtotal is number
  output:
    total is number
    note is optional text
  return map:
    "total" is subtotal + 1
```

Call a function with call function.

```
let result is call function "apply tax":
  subtotal is 10
```

Rules

- Functions are pure by default
- Functions cannot call tools or ai
- Functions cannot write records
- Return must exist

## Operators

Math operators

- Addition
- Subtraction
- Multiplication
- Division
- Modulo
- Exponentiation (**)
- Unary minus

Comparison operators

- Equal
- Not equal
- Less
- Less or equal
- Greater
- Greater or equal
- Between (inclusive)
- Strictly between (exclusive)

Boolean operators

- And
- Or
- Not

Precedence order (highest to lowest)

- Exponentiation
- Unary
- Multiply and divide and modulo
- Add and subtract
- Comparison (including between)
- Not
- And
- Or

Notes
- `**` is right-associative: `2 ** 3 ** 2` is `2 ** (3 ** 2)`.
- Unary minus binds as `-(2 ** 2)`.

## Let blocks

Group consecutive lets with a block:

```
let:
  a is 10
  b is 5
  c is a + b
```

Inline entries are allowed inside the block:

```
let:
  a is 10, b is 5, c is a + b
```

## Calc blocks

Calc blocks are formula-style assignments that desugar to lets (or sets for state paths):

```
calc:
  total = 2 * 3
  state.total = total
```

## Bounded loops

Use repeat while with a required limit.
The limit must be a positive integer literal.
When the limit is hit the runtime raises an error.

```
let count is 0
repeat while count is less than 2 limit 3:
  set count is count + 1
```

## List values

List literal

```
let numbers is list:
  1,
  2,
```

List operations

```
let length is list length of numbers
let more is list append numbers with 3
let first is list get numbers at 0
```

## List aggregations

Aggregations are built-in expressions and require numeric lists. Empty lists raise an error.

```
let total is sum(numbers)
let avg is mean(numbers)
```

## List transforms

Map/filter/reduce are expression forms with scoped binders and block bodies:

```
let doubled is map numbers with item as n:
  n * 2

let big is filter doubled with item as x:
  x is greater than 5

let total is reduce big with acc as s and item as v starting 0:
  s + v
```

## Map values

Map literal

```
let data is map:
  "count" is 2
  "label" is "ok"
```

Map operations

```
let value is map get data key "label"
let updated is map set data key "extra" value "yes"
let keys is map keys updated
```
