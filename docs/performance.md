# Performance, Scalability, and Production Hardening

This phase adds explicit runtime performance controls without changing `.ai` grammar.

## Capability gate

Performance features are opt-in through the `performance` capability.

```ai
capabilities:
  performance
```

Legacy `performance_scalability` remains accepted for backward compatibility, but new work should use `performance`.

## Configuration

Set performance controls in `namel3ss.toml`:

```toml
[performance]
async_runtime = true
max_concurrency = 8
cache_size = 128
enable_batching = true
metrics_endpoint = "/api/metrics"
```

Equivalent runtime flags:

```bash
n3 run --async-runtime true --max-concurrency 8 --cache-size 128 --enable-batching true app.ai
```

Environment overrides:

- `N3_ASYNC_RUNTIME`
- `N3_MAX_CONCURRENCY`
- `N3_CACHE_SIZE`
- `N3_ENABLE_BATCHING`
- `N3_PERFORMANCE_METRICS_ENDPOINT`

## Runtime behavior

- AI text calls use an explicit deterministic cache key.
- Scheduler limits interactive and heavy work using deterministic bounded semaphores.
- Embedding ingestion supports deterministic batching while preserving input order.
- Existing runtime outputs remain unchanged.

## Determinism

- Enabling performance mode does not change final outputs for the same input.
- Cache keys include provider, model, prompt, tools, and memory payload.
- Batching preserves request order and response order.
- Scheduler only controls concurrency limits; it does not reorder flow steps.

## Error behaviour

- If performance settings are enabled without `performance`, runtime startup fails with a clear message.
- Invalid config values (negative cache size, zero concurrency, invalid booleans) fail fast before execution.
- Cache misses fall back to direct computation.
- Scheduler failures propagate as runtime errors; no silent fallbacks.

## Observability

When observability is enabled, performance counters are emitted under metrics names:

- `performance_ai_cache_hit`
- `performance_ai_cache_miss`
- `performance_scheduler_wait_ms`
