# namel3ss RAG v1 Operations Runbook

## Scope
- Operate RAG v1 in production with deterministic replay and citation guarantees.
- Keep deployment, migration, and release checks reproducible.

## Preflight
- Confirm all required tests are green.
- Confirm migration manifest hash and deployment profile hash are pinned.
- Confirm evaluation regression report status is `pass`.
- Confirm runbook section coverage is complete.

## Deployment
- Use a normalized deployment profile with:
 - `environment` set to `production`
 - `replicas` set to `2` or higher
 - `stream_transport` set to `sse`
 - service SLO targets defined
- Apply deployment profile in canonical JSON order.

## Migration Replay
- Run migration manifest in dry-run mode first.
- Validate dry-run report:
 - `status` is `applied` or `noop`
 - `replay_safe` is `true`
 - no failed steps
- Apply migration manifest once in write mode.
- Re-run the same manifest and confirm status `already_applied`.

## Load And Soak
- Execute deterministic load and soak validation with fixed fixture traffic.
- Minimum acceptance targets:
 - requests total meets deployment load target
 - soak duration meets deployment load target
 - success rate meets SLO availability target
 - p95 and p99 latency meet SLO targets
 - retrieval drift is below SLO cap
 - citation grounding meets SLO floor

## Release Gate
- Build release readiness report with:
 - deployment profile
 - migration report
 - evaluation regression report
 - load and soak result
 - runbook status
- Block release if any required gate fails.

## Rollback
- Roll back deployment profile to last known-good profile hash.
- Keep migration manifests idempotent and forward-safe; do not use destructive rollback scripts.
- Re-run release gate after rollback and confirm required gates pass.
