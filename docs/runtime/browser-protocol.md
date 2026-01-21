# Browser Protocol

The App Runtime server that `n3 run` starts exposes a single browser protocol. This doc freezes the surface and ordering.

## Scope
- One process serves the UI shell at `/` and JSON APIs under `/api/*`.
- Applies to `n3 run` in run/preview/dev; Studio is separate.
- Payloads use canonical JSON serialization (stable key ordering, no timestamps).

## Endpoints
### GET /api/ui
- Returns the UI manifest for the current program produced by the runtime manifest builder.
- Includes `ok`, `pages`, `actions`, `revision`, and any `contract` or `errors` fields surfaced by validation.
- Order matches source order; action ids are deterministic.

### GET /api/state
- Returns `{"ok": true, "state": {...}, "records": [...], "revision": "<hash>"}` when the program loads.
- `records` is a deterministic snapshot of record collections (ordered by record declarations and record ids).
- `effects` may be included to summarize the most recent data changes in a deterministic order.
- If load fails, returns `{"ok": false, "error": {...}, "revision": "<hash>"}`.

### POST /api/action
- Body: `{"id": "<action id>", "payload": {}}` with `Content-Type: application/json`.
- Response mirrors the existing action response schema: `ok`, `state` snapshot, `revision`, and optional `overlay` and `error` keys for failures.
- Errors are deterministic engine payloads; invalid bodies return an engine error payload with HTTP 400.

### POST /api/upload
- Accepts multipart form data or chunked upload bodies.
- Stores uploads under the scoped runtime store and returns deterministic metadata.
- Response includes `ok`, `upload`, and `traces` (upload received and stored).

### GET /api/uploads
- Returns `{"ok": true, "uploads": [...]}` with deterministic ordering.
- Upload entries include logical name, size, checksum, and scoped stored path.

### GET /api/logs
- Returns `{"ok": true, "count": <number>, "logs": [...]}` with deterministic ordering.
- Logs are structured events with stable ids, levels, messages, and optional fields.

### GET /api/trace
- Returns `{"ok": true, "count": <number>, "spans": [...]}` with deterministic ordering.
- Spans include stable ids, names, parent relationships, status, and step ranges.

### GET /api/metrics
- Returns `{"ok": true, "counters": [...], "timings": [...]}` with deterministic ordering.
- Counters and timings include stable labels and step-based timing data.

### GET /api/health
- Returns `{"ok": true, "status": "ready", "mode": "<run|dev|preview>"}` with no timestamps.

## Determinism guarantees
- Ports start at 7340 and increment deterministically when occupied.
- Revisions derive from source content hashing; identical sources yield identical revisions.
- JSON serialization is canonical and ordered; no timestamps, host paths, or random ids appear in payloads.
- Secrets are redacted and host paths are scrubbed in observability payloads.
- Runtime artifacts remain under `.namel3ss/` and are ignored by git; running the server must not dirty the repo.

## UI shell
- `/` serves the runtime HTML shell that pulls `/api/ui` and `/api/state` and triggers `/api/action`.
- The shell is shared by run/preview; Studio uses a separate UI.
