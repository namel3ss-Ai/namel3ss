# Performance Guide

## Goals
- Keep compile/build latency predictable for large manifests.
- Keep memory growth visible and bounded.
- Preserve deterministic outputs while optimizing.

## Profiling Workflow
1. Run `n3 build app.ai --profile --profile-iterations 3 --json`.
2. Inspect `performance_profile.json` in the build bundle.
3. Track these fields across runs:
   - `metrics[].elapsed_ms`
   - `metrics[].peak_memory_kb`
   - `manifest_bytes`, `page_count`, `element_count`, `action_count`

## Stage Definitions
- `load_program`: parse and lower source modules.
- `build_manifest`: lower IR to UI manifest.
- `serialize_manifest`: canonical JSON serialization.

## Determinism Rules
- Stage ordering is fixed.
- Output keys are canonically sorted.
- Profiling can be disabled; disabled output shape is still stable.

## Regression Checks
- Add baseline snapshots for large apps.
- Fail CI when structural metrics drift unexpectedly:
  - manifest bytes
  - page/element/action counts
- Track latency trends without asserting exact wall-clock values.
