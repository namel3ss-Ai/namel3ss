# Streaming and Interactive Responses

Streaming shows AI output incrementally while preserving the same final result.

## Enable capability

```ai
capabilities:
  streaming
```

## Per-call streaming

```ai
ask ai "assistant" with stream: true and input: "Explain photosynthesis." as reply
```

- `stream` is optional and defaults to `false`.
- `stream` accepts only `true` or `false`.
- `stream: true` requires the `streaming` capability.

## Transport

- Studio uses `POST /api/action/stream` with `text/event-stream`.
- Events are deterministic and ordered by `sequence`.
- Event types: `progress`, `token`, `finish`, `return`.

## Determinism

- Streaming does not change final output text.
- Token order is stable for the same input and seed.
- Intermediate events are not written into flow state.

## Error behaviour

- Missing `streaming` capability fails at compile time.
- Unsupported provider streaming fails at compile time.
- Transport cancellation returns a controlled error to the caller.
