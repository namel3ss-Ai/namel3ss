# Backend Capabilities

Backend Capabilities are built-in, dependency-free capabilities that let apps perform backend work while keeping the language boundary deterministic and explicit.

These capabilities are deny-by-default. Apps must opt in with a `capabilities` block.

## Enable built-in capabilities
```ai
capabilities:
  http
  jobs
  files
```

## HTTP calls (read-only)
Declare an HTTP tool using the normal tool syntax and set its implementation to `http`.

```ai
tool "fetch status":
  implemented using http

  input:
    url is text
    method is optional text
    headers is optional json
    timeout_seconds is optional number

  output:
    status is number
    body is text
```

Rules:
- Only `GET` is supported. `method` defaults to `GET` when omitted.
- `headers` is a JSON object of string keys and values.
- `body` input is not supported for read-only HTTP.
- Output fields are explicit and deterministic. `headers` output is a JSON list of `{ name, value }` pairs sorted by name then value.
- `json` output is available only when the response body is valid JSON.

Studio shows the request definition (method, url, headers) and a response summary.

## Background jobs
Jobs are language-level blocks that run deterministically after a flow or when state changes.

```ai
job "persist entry" when state.persist_pending is true:
  create "Entry" with state.pending_entry as entry
  set state.persist_pending is false
```

Triggering jobs:
- `enqueue job "name"` schedules a job from a flow.
- `when <expression>` triggers when a boolean expression flips from `false` to `true`.

Determinism:
- Jobs run in FIFO order based on enqueue order.
- `when` triggers are evaluated at stable points in the run.
- No time-based scheduling or cron is available.

Studio shows job enqueued, job started, and job finished events.

## File I/O (scoped, local-only)
Declare a file tool using `implemented using file`.

```ai
tool "read note":
  implemented using file

  input:
    operation is text
    path is text

  output:
    content is text
    ok is boolean
    bytes is number
```

Rules:
- `operation` must be `read` or `write`.
- `path` must be relative (no absolute paths or `..`).
- Files are scoped under `.namel3ss/files/<app-scope>/` and never expose host paths.
- Read operations return `content`, `ok`, and `bytes`.
- Write operations return `ok` and `bytes` (no `content`).

Studio shows file operations with the scoped path and result summary.

## Determinism and safety
- All capability use is explicit and deny-by-default.
- No timestamps, random ids, or host paths are surfaced.
- HTTP and file outputs are canonicalized for stable ordering.
- Job scheduling is deterministic and controlled by the runtime.
