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
- Unary minus

Comparison operators

- Equal
- Not equal
- Less
- Less or equal
- Greater
- Greater or equal

Boolean operators

- And
- Or
- Not

Precedence order

- Unary
- Multiply and divide and modulo
- Add and subtract
- Comparison
- And
- Or

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
  1
  2
```

List operations

```
let length is list length of numbers
let more is list append numbers with 3
let first is list get numbers at 0
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
