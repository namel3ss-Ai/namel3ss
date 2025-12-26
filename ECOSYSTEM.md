# namel3ss Ecosystem

This document defines how capsules become trusted packages and how the index stays curated.

## Trust tiers

- **official**: maintained by the namel3ss core team, reviewed for safety, and used as reference packages.
- **verified**: community-maintained packages that pass validation, tests, and governance checks.
- **community**: packages listed for discovery but not verified by the core team.

## Quality rules (applies to every indexed package)

- `capsule.ai` exists with explicit exports.
- `LICENSE` is present and declared in metadata.
- `checksums.json` is present and matches contents.
- No install scripts or hooks (no postinstall/preinstall/prepare).
- Deterministic, offline tests and examples.

## How to get verified

1) Publish a package repo with `namel3ss.package.json` and `checksums.json`.
2) Run:
   - `n3 pkg validate .`
   - `n3 test`
   - `n3 verify --prod` (if an example app exists)
3) Open a PR to the index repo with your entry and requested trust tier.
4) Keep release tags and checksums stable.

## What “official” means

- Maintained by the namel3ss team.
- Reviewed for determinism, licensing, and clarity.
- Used as reference implementations for the ecosystem.

## Official index

The curated index lives in a GitHub repo (file-based, no service):
- `namel3ss-ai/index` → `index.json` (schema_version=1)

The CLI defaults to `resources/pkg_index_v1.json`, and you can override via:
- `N3_PKG_INDEX_PATH=/path/to/index.json`
- `N3_PKG_INDEX_URL=https://.../index.json`
