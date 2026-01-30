# Operations

## Purpose
- Define a production template skeleton for operations apps.
- Establish structure and guarantees; functionality is added incrementally.

## Entry
- Entry file: `app.ai`.
- CLI wiring is defined outside this folder.

## Contracts
- Deterministic only: no timestamps, randomness, host paths, or secrets.
- Offline by default; no network or external services required.
- Explain surfaces are required and must be documented when flows exist.
- Runtime artifacts remain under `.namel3ss/` and stay out of git.

## Explain
No explain output yet; this skeleton contains no flows or runtime behavior.

## Fixtures
None.

## Verify
- `n3 app.ai check`
