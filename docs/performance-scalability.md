# Performance and Scalability

This phase improves runtime concurrency without changing DSL grammar.

## Runtime server model

Runtime servers now support deterministic threaded serving through `concurrency.yaml`.

```yaml
server_mode: threaded
max_threads: 8
worker_processes: 1
require_free_threaded: false
compiled_cache_enabled: true
```

Defaults:

- `server_mode`: `threaded`
- `max_threads`: `8`
- `worker_processes`: `1`
- `require_free_threaded`: `false`
- `compiled_cache_enabled`: `true`

Supported server modes:

- `single`
- `threaded`

## Free-threaded Python compatibility

If `require_free_threaded` is true, startup fails unless Python reports free-threaded mode.
This keeps behavior explicit and deterministic across environments.

## Deterministic concurrency safeguards

- Shared runtime state uses explicit locks.
- Route registry updates and route matching are lock-protected.
- Program reload state uses parse caching and lock-protected refresh.
- Threaded server concurrency is bounded by `max_threads`.

## Health payload

`/api/health` includes concurrency details in runtime server responses where available.
