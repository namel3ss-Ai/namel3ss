# Backend Capabilities

Backend Capabilities are built-in, dependency-free capabilities that let apps perform backend work while keeping the language boundary deterministic and explicit.

These capabilities are deny-by-default. Apps must opt in with a `capabilities` block.

## Enable built-in capabilities
```ai
capabilities:
  http
  jobs
  scheduling
  files
  uploads
  secrets
  vision
  speech
  training
  streaming
  performance
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

Built-in HTTP support is intentionally read-only (`GET`). Write methods introduce side effects and additional risk. `POST` / `PUT` / `DELETE` should be implemented via explicitly governed packs, not implicitly added. This keeps HTTP capabilities deterministic and inspectable.

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
- Scheduling uses a logical clock (see below); no wall-clock scheduling or cron.

Studio shows job enqueued, job started, and job finished events.

## Scheduling (logical time)
Scheduling runs jobs later without wall clocks. Time only moves when the program advances it.

```ai
capabilities:
  jobs
  scheduling

flow "demo":
  enqueue job "refresh" after 2
  tick 2
  return "done"
```

Rules:
- `after` schedules relative to the current logical time.
- `at` schedules at a specific logical time.
- `tick <number>` advances the logical clock by a whole number.
- Jobs become eligible only when logical time reaches the due time.
- Order is deterministic: due time, enqueue order, then job name.

Studio shows job scheduled and logical time advanced events.

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

## Uploads (multipart + streaming-safe)
Uploads accept multipart form data or streaming (chunked) bodies and store files under the scoped runtime store.

```ai
capabilities:
  uploads
```

Rules:
- Uploads write under `.namel3ss/files/<app-scope>/uploads/`.
- Metadata is deterministic: `bytes`, `checksum`, and `content_type`.
- Uploads are deny-by-default and must be explicitly enabled.
- Upload responses include deterministic trace events for upload received and stored.

Endpoints:
- `POST /api/upload` with multipart or chunked data.
- `GET /api/uploads` to list stored uploads.

Use `X-Upload-Name` or `?name=` to set a logical filename when the client does not send one.

## Vision and speech (multi-modal AI input)
Vision and speech capabilities gate image/audio AI input modes.

```ai
capabilities:
  vision
  speech
```

Use in flows:

```ai
ask ai "assistant" with image input: state.image_path as image_reply
ask ai "assistant" with audio input: state.audio_path as audio_reply
```

Rules:
- `image` mode requires `vision`.
- `audio` mode requires `speech`.
- Provider capability checks run at compile time.
- Input normalization is deterministic (hash + canonical payload + derived seed).
- Content filtering is deterministic and explicit.

## Training (custom model fine-tuning)
Training enables `n3 train` for deterministic, sandboxed custom model fine-tuning.

```ai
capabilities:
  training
```

Example:

```bash
n3 train --model-base gpt-3.5-turbo \
  --dataset data/support_tickets.jsonl \
  --epochs 3 \
  --learning-rate 2e-5 \
  --output-name supportbot.faq_model_v2
```

Rules:
- Training is disabled unless `training` capability is declared in the app.
- Training inputs are deterministic: dataset snapshot hash, seed, and split are recorded.
- Registered model names are immutable; existing names are not overwritten.
- Training writes artifacts under `models/<output_name>/<version>/` and updates `models_registry.yaml`.
- Evaluation metrics are written to `docs/reports/training_metrics_<name>_<version>.json`.

## Streaming AI responses
Streaming is opt-in per AI call and gated by the `streaming` capability.

```ai
capabilities:
  streaming

flow "demo":
  ask ai "assistant" with stream: true and input: "Explain photosynthesis." as reply
  return reply
```

Rules:
- `stream: true` is allowed only on `ask ai`.
- Providers must explicitly support streaming.
- Streaming events are emitted in deterministic sequence order.
- Final output is identical to non-streaming output for the same input and seed.

## Performance runtime controls
Performance controls are configured outside `.ai` and are gated by `performance`.

```ai
capabilities:
  performance
```

Configure in `namel3ss.toml`:

```toml
[performance]
async_runtime = true
max_concurrency = 8
cache_size = 128
enable_batching = true
```

Rules:
- Without `performance`, enabled performance settings fail fast with guidance.
- Deterministic caching keys include model and input payload.
- Batching preserves request/response ordering.
- Async execution does not change final results for the same input.

## Secrets and auth helpers
Secrets are loaded from `.namel3ss/secrets.json` or environment variables and are always redacted in traces.
Environment variables use `N3_SECRET_<NAME>` or `NAMEL3SS_SECRET_<NAME>`.

```ai
capabilities:
  http
  secrets

flow "call_api":
  let headers is auth_bearer(secret("stripe_key"))
  let response is fetch status:
    url is "https://example.com"
    headers is headers
  return response
```

Define the HTTP tool as shown in the HTTP section above.

Helpers:
- `secret("name")` loads a secret by name.
- `auth_bearer(secret("name"))` builds an Authorization header.
- `auth_basic(secret("user"), secret("password"))` builds basic auth.
- `auth_header("X-API-Key", secret("name"))` sets a custom header.

Rules:
- Secrets require the `secrets` capability.
- Auth helpers require both `http` and `secrets` capabilities.
- Studio shows redacted headers like `Authorization: Bearer [redacted: stripe_key]`.

## Determinism and safety
- All capability use is explicit and deny-by-default.
- No timestamps, random ids, or host paths are surfaced.
- HTTP and file outputs are canonicalized for stable ordering.
- Job scheduling is deterministic and controlled by the runtime.
- Upload metadata is checksum-based and ordered deterministically.
- Secrets are redacted from traces and outputs.
