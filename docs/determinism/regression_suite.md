# Determinism Regression Suite

Evolution Edition makes repeat-run stability a first-class CI signal.

## Core Checks

- Repeated compile of the same app must produce byte-identical manifest JSON.
- Repeated retrieval trace generation must produce byte-identical trace JSON.
- Include warnings and composition source-map output must be stable.
- UI baselines must match checked-in goldens.

## Local Commands

```bash
python tools/determinism_repeat_check.py app.ai
python tools/ui_baseline_refresh.py --check
python -m namel3ss.beta_lock.repo_clean
```

## CI Policy

Determinism failures are blocking:

- No timestamps or random IDs in compiler/runtime artifacts.
- No absolute paths in manifests, diagnostics payloads, or emitted composition metadata.
- Warning and error ordering remains stable across runs.
