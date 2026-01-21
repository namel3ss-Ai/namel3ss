# Observability

Deterministic logging, tracing, and metrics for namel3ss. Outputs are structured, ordered, and scrubbed for safety.

## Structured logging
Use `log` statements to emit structured events from flows and jobs.

```ai
flow "ship order" requires true:
  log info "Order shipped" with map:
    "order_id" is input.id
    "region" is input.region
  return "ok"
```

Log entries include:
- level: debug, info, warn, or error
- message
- optional fields object

Logs attach to the current span when a span is active.

## Tracing
Spans are emitted automatically for actions, jobs, tools, and capabilities (HTTP, file, uploads, and packs). Each span includes a stable id, name, kind, status, and parent relationship when nested. Timing is measured in logical steps, not wall time.

When running with `--debug`, transient outputs may include wall time in developer-only views. Stable outputs never include timestamps.

## Metrics
Counters and timings are deterministic and order-stable.

```ai
flow "track usage" requires true:
  metric counter "requests" increment
  metric counter "requests" add 2 with map:
    "route" is "/api/orders"
  metric timing "render" record 5
  return "ok"
```

Metric operations:
- counter: increment, add, set
- timing: record

Timings use logical steps. Automatic timings are recorded for actions, jobs, and capabilities.

## Storage
Runtime output is stored under:
- `.namel3ss/observability/logs.json`
- `.namel3ss/observability/trace.json`
- `.namel3ss/observability/metrics.json`

## Redaction and determinism
- Secrets are replaced with `***REDACTED***`.
- Host paths are replaced with `<path>`.
- Outputs are ordered and stable; no timestamps appear in stable payloads.

## Studio
Studio surfaces Logs, Tracing, and Metrics in dedicated panels alongside other explainability views.

## Runtime endpoints
- `GET /api/logs` returns `ok`, `count`, and `logs`.
- `GET /api/trace` returns `ok`, `count`, and `spans`.
- `GET /api/metrics` returns `ok`, `counters`, and `timings`.

All payloads are structured, scrubbed, and ordered.
