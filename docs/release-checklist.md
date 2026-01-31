# Release Checklist

Use this checklist before tagging a release. All commands must pass with a clean working tree.

## Install + Verify
```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
n3 --version
n3 doc
python tools/package_verify.py
```

## Embedding Verification (C)
```bash
python -m pytest -q tests/embed/test_embed_c_example.py
```

## Core Verification
```bash
PYTHONDONTWRITEBYTECODE=1 python -m compileall src -q
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
python tools/responsibility_check.py
python -m namel3ss.beta_lock.repo_clean
git status --porcelain
```

## Benchmark Artifact (Non-gating)
```bash
python tools/bench.py --out .namel3ss/ci_artifacts/bench_report.json --iterations 1 --timing deterministic
```
