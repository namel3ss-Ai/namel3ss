# Release Checklist

Use this checklist before tagging a release. All commands must pass with a clean working tree.

## Install + Verify
```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev]"
n3 --version
n3 doc
python3 tools/package_verify.py
```

## Embedding Verification (C)
```bash
python3 -m pytest -q tests/embed/test_embed_c_example.py
```

## Core Verification
```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m compileall src -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q
python3 tools/spec_freeze_check.py
python3 tools/responsibility_check.py
python3 -m namel3ss.beta_lock.repo_clean
git status --porcelain
```

## Benchmark Artifact (Non-gating)
```bash
python3 tools/bench.py --out .namel3ss/ci_artifacts/bench_report.json --iterations 1 --timing deterministic
```

## Release Notes
- Ensure the CHANGELOG entry for the version explicitly states grammar/runtime change status (for example: “No grammar/runtime changes.”).
