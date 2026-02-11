# Upgrade guide

This guide lists breaking changes and the manual steps to move between versions.

## 0.1.0a17

### Breaking changes
- None.

### Behavior updates to review
- None.

### How to detect breaking changes
- Run `n3 app.ai check` and verify new warnings are expected.

### How to fix or migrate manually
- No migration required.

## 0.1.0a15

### Breaking changes
- None.

### Behavior updates to review
- Legacy debug-oriented chat subcomponents (`thinking`, legacy `citations`, `memory`) now surface diagnostics placement warnings when mixed into product layouts.
- Versioned headless UI and plugin asset endpoints now return deterministic `ETag` and cache headers and may answer `304 Not Modified` for conditional GETs.
- Studio/runtime now loads plugin assets from `manifest.ui.plugins`; plugin scripts should tolerate repeated manifest refreshes and idempotent mounting.

### How to detect breaking changes
- Run `n3 app.ai check` and verify new warnings are expected.
- Run `n3 app.ai ui --json` and confirm `manifest.warnings` and `manifest.theme` align with expected behavior.
- Run release suites:
  - `pytest -q tests/ui/test_ui_manifest_baseline.py tests/ui/test_warning_pipeline.py`
  - `pytest -q tests/runtime/test_browser_api_first.py tests/runtime/test_service_runner.py`

### How to fix or migrate manually
- Move diagnostics-style UI into `layout: diagnostics:` blocks or keep them explicitly debug-only.
- If your frontend uses `/api/v1/ui`, support conditional requests (`If-None-Match`) and `304` responses.
- If you ship custom plugins, verify asset URLs declared in plugin manifests resolve and load in both Studio and runtime.

## 0.1.0a14

### Breaking changes
- None in this release.

### How to detect breaking changes
- Run `n3 app.ai check` to surface schema/contract changes before runtime.
- Run `n3 when app.ai` to see spec compatibility warnings.

### How to fix or migrate manually
- Revert incompatible edits or update the source to match the current contracts.
- If the spec version changes, use `n3 migrate app.ai --to 1.0` (deterministic, no runtime side effects).
- Re-run `n3 app.ai check` until warnings/errors are resolved.

## 0.1.0a13

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
