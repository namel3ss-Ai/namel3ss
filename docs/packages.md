# Packages (Capsule Dependencies)

Packages let you reuse Capsules across projects. A package is just a Capsule stored under `packages/<name>/` with metadata and checksums.

Key idea:
- pkg = reusable Capsules, installed locally, never executed.

## Add and install

Declare dependencies in `namel3ss.toml`:

```toml
[dependencies]
inventory = "github:owner/repo@v0.1.0"
```

Commands:
```
n3 pkg add github:owner/repo@v0.1.0
n3 pkg install
```

Packages install into `packages/<name>/`. Imports stay the same:

```ai
use "inventory" as inv
```

Resolution order:
1) `modules/<name>/capsule.ai`
2) `packages/<name>/capsule.ai`

## Lockfile

`n3 pkg install` writes `namel3ss.lock.json` with:
- resolved versions
- provenance (GitHub ref)
- checksums
- licenses

The lockfile is deterministic and should be committed for reproducible installs.

## Debug and inspect

```
n3 pkg tree
n3 pkg why inventory
n3 pkg plan
n3 pkg verify
n3 pkg licenses
```

Notes:
- Packages must declare a license and checksums.
- No install scripts or postinstall hooks are ever run.
