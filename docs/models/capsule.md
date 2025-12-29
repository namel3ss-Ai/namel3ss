# Capsule

A capsule groups flows and records into a module you can reuse.
Capsules are used for packages and legacy module folders.
Use module files for local reuse in an app.

**Example**
```ai
use "inventory" as inv

flow "seed":
  return inv.seed_item
```

**Command**
- `n3 graph`
