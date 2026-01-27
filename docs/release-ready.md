# Release readiness

This document defines what "release-ready" means for namel3ss and how to validate it.

## What release-ready means
- The full test suite passes (unit, golden, doc, parity, and e2e).
- Golden outputs, manifests, and trace schemas match their locked contracts.
- Reference apps pass the same gates as the core.
- The repository is clean after tests (no drift, no unexpected writes).

## How to run full release checks locally
Run these from the repo root:

1) Full test suite
```bash
python -m pytest -q
```

2) Build + start smoke tests
```bash
python -m pytest -q tests/runtime/test_production_server.py
```

3) Contract gates
```bash
n3 expr-check --json .namel3ss/expr_report.json
n3 release-check --json .namel3ss/release_report.json --txt .namel3ss/release_report.txt
n3 verify --dx --json
```

4) Repository cleanliness
```bash
python -m namel3ss.beta_lock.repo_clean
```

## Release invariants
- Canonical order: VERSION bump → tests (CI) → tag (vX.Y.Z) → PyPI publish → Docker image → release notes.
- VERSION is the source of truth for release artifacts; tags must match VERSION (optional leading `v`).
- Docker images install from the local source tree; VERSION bumps alone never affect docker builds.
- PyPI is only used during publish; Docker builds never depend on PyPI availability.
- Each release emits a manifest artifact with version, commit, tag, PyPI hashes, and docker tag.

## Guarantees
- Deterministic outputs for identical inputs.
- Locked grammar, manifest, and trace contracts.
- English-first errors and fix hints.
- Studio remains optional and purely inspectable.

## Not guaranteed
- External provider availability or network uptime.
- Performance across all workloads or datasets.
- Automatic migration of breaking changes.

## Reference apps
Reference apps are read-only and treated as contract tests.

- `evals/apps/reference_release_hub` — release planning with UI, agents, stories, access control, and media.
