# Final Integration And Release Polish

This document captures the release-hardening pass after the UI/runtime expansion work.

## Goals

- Validate that new features interoperate without hidden regressions.
- Keep deterministic behavior across compiler, manifest, runtime, and headless API paths.
- Lock down release docs, migration notes, and CI guardrails.

## Integration Matrix

Verified combinations in tests and baseline fixtures:

- Layout slots + responsive collapse + sticky regions.
- Conditional rendering + empty-state suppression.
- RAG components + chat + diagnostics separation.
- Upload actions + required upload gating + headless action dispatch.
- Theme tokens + diagnostics panel rendering.
- Plugin assets + custom-component rendering surfaces.
- Headless API + auth + CORS + cache validation.

## Performance And Runtime Hardening

- Added deterministic `ETag` support for `GET /api/v1/ui`.
- Added conditional request handling (`If-None-Match` -> `304`) for versioned headless UI responses.
- Added immutable cache headers and `ETag` support for plugin assets served from `/api/plugins/...`.
- Added renderer-side deterministic plugin asset loading to avoid repeated script/style injection.

## Determinism Notes

- Versioned API payload hash remains the source for headless cache validators.
- Plugin asset `ETag` values are derived from asset bytes using SHA-256.
- Baseline manifest warnings include diagnostics-placement checks for legacy debug-style chat elements.

## Release Candidate Checklist

Run this before tagging:

1. `python -m compileall src -q`
2. `python tools/line_limit_check.py`
3. `python tools/responsibility_check.py`
4. `pytest -q tests/ui/test_ui_manifest_baseline.py tests/ui/test_warning_pipeline.py`
5. `pytest -q tests/runtime/test_browser_api_first.py tests/runtime/test_service_runner.py tests/runtime/test_production_server.py`
6. `pytest -q tests/studio/test_studio_web_structure.py tests/studio/test_studio_diagnostics_panel.py`
7. `n3 app.ai check` on representative apps (chat, RAG, uploads, plugins, diagnostics)

## Release Artifacts

- `CHANGELOG.md` entry for the new release.
- `UPGRADE.md` migration notes for behavior-level changes.
- `docs/headless-api-openapi.json` as the versioned headless API reference.
