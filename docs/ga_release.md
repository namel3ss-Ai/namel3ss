# GA Release Guide

This document defines GA readiness and release responsibilities for Namel3ss 1.0+.

## GA readiness checklist

- public API boundaries documented and enforced
- compatibility and deprecation policies published
- release pipeline produces reproducible artifacts
- governance and security docs are current
- deterministic and contract test gates pass

## Release artifacts

- Python distribution artifacts
- container image metadata
- manifest/checksum reports for reproducibility
- changelog and release notes

## Required automated checks

Run before tagging:

```bash
python -m compileall src -q
python -m pytest -q
python tools/line_limit_check.py
python tools/responsibility_check.py
python tools/release/checklist.py
```

## Release ownership

- Chair approves release readiness.
- Secretary verifies docs and changelog consistency.
- Security maintainer confirms no unresolved critical advisories.

## Long-term support (LTS)

- GA minor series receives security and stability fixes.
- deprecated features follow the deprecation policy window before removal.
- major-version transitions require migration guides and explicit upgrade notes.
