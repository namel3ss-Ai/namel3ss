# Modules and Tests

This page covers the Phase 2 project structure: Capsules (modules) and the built-in test runner.

## Capsules (modules)

Modules live under `modules/<name>/` and are defined by a capsule contract:

```
modules/inventory/capsule.ai
modules/inventory/logic.ai
```

`capsule.ai` declares the public API:

```ai
capsule "inventory":
  exports:
    record "Product"
    flow "seed_item"
```

Everything else in the module stays private.

## Using modules

Import a module with `use` and a required alias:

```ai
use "inventory" as inv

page "home":
  form is "inv.Product"
  button "Seed":
    calls flow "inv.seed_item"
  table is "inv.Product"
```

Rules:
- Modules resolve only from `modules/<name>/capsule.ai`.
- Cross-module references must be alias-qualified (for example `inv.Product`).
- Only exports listed in `capsule.ai` are visible outside the module.

Inspect the module graph and exports:

```
n3 app.ai graph
n3 app.ai exports
```

## Tests (`n3 test`)

Test files live under `tests/` and must end with `*_test.ai`.

```ai
test "smoke":
  run flow "seed_item" with input: {} as result
  expect value is "seeded"
```

Run tests from the project root:

```
n3 test
n3 test --json
```
