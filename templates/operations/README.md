# Operations

## Purpose
- Provide deterministic job lifecycle tracking with replayable execution narratives.
- Surface explicit failure, retry, rollback, and summary signals for operations.

## Entry
- Entry file: `app.ai`.
- CLI wiring is defined outside this folder.

## Contracts
- Deterministic only: no timestamps, randomness, host paths, or secrets.
- Job ids are stable inputs (`job_id`) and are required for all flows.
- Lifecycle states are explicit and limited to: queued, running, blocked, done.
- Transitions emit explain records with previous/next state and stable reason codes.
- Failure classification is stable: input, policy, dependency, internal.
- Retries are bounded and recorded with ordered attempt numbers.
- Rollback is explicit with reason codes and artifact ids.
- Execution narrative is stored in `ExecutionEvent` and is replayed without side effects.
- Job ordering in summaries is stable: queued -> running -> blocked -> done.
- Drift uses expected vs actual outcomes; cost reports `not_available` unless extended.
- Offline by default; no network or external services required.
- Runtime artifacts remain under `.namel3ss/` and stay out of git.

## Explain
- ExplainEntry records lifecycle transitions, failure classification, retries, rollback, and summaries.

## Fixtures
- See `tests/fixtures/operations/`.

## Verify
- `n3 app.ai check`
