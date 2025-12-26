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
n3 pkg search auth
n3 pkg info auth-basic
n3 pkg add auth-basic
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

## Official index (curated)

namel3ss ships a curated package index as a JSON file (schema_version=1). The CLI reads it from:
- `resources/pkg_index_v1.json` (default)
- `N3_PKG_INDEX_PATH=/path/to/index.json` (override)
- `N3_PKG_INDEX_URL=https://.../index.json` (optional)

Use the index for discovery:
```
n3 pkg search audit
n3 pkg info audit-trail
n3 pkg add audit-trail
```

## Validate and scaffold

Validate a package before publishing:
```
n3 pkg validate .
n3 pkg validate github:owner/repo@v0.1.0
n3 pkg validate --strict
```

Scaffold a new package:
```
n3 new pkg my_capsule
```
