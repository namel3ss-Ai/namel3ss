# Capsule

A capsule groups flows and records into a module you can reuse.

**Example**
```ai
use "inventory" as inv

flow "seed":
  return inv.seed_item
```

**Command**
- `n3 graph`
