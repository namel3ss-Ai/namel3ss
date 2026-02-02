# Upgrade guide

This guide lists breaking changes and the manual steps to move between versions.

## 0.1.0a12

### Breaking changes
- None in this release.

### How to detect breaking changes
- Run `n3 app.ai check` to surface schema/contract changes before runtime.
- Run `n3 when app.ai` to see spec compatibility warnings.

### How to fix or migrate manually
- Revert incompatible edits or update the source to match the current contracts.
- If the spec version changes, use `n3 migrate app.ai --to 1.0` (deterministic, no runtime side effects).
- Re-run `n3 app.ai check` until warnings/errors are resolved.

## 0.1.0a10

### Breaking changes
- None in this release.

### How to detect breaking changes
- Run `n3 app.ai check` to surface schema/contract changes before runtime.
- Run `n3 when app.ai` to see spec compatibility warnings.

### How to fix or migrate manually
- Revert incompatible edits or update the source to match the current contracts.
- If the spec version changes, use `n3 migrate app.ai --to 1.0` (deterministic, no runtime side effects).
- Re-run `n3 app.ai check` until warnings/errors are resolved.
