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

### GET /api/data/status
- Returns backend status including target, kind, enabled flag, descriptor, and replica hints.
- Includes last export/import summaries when present.
- Payloads are redacted; no host paths or secrets appear.

### GET /api/migrations/status
- Returns migration status with plan ids, pending state, breaking flags, and reversibility.
- `plan_changed` is true when the stored plan id differs from the current plan.

### GET /api/migrations/plan
- Returns the last recorded migration plan when present, otherwise the current plan.
- `changes` and `breaking` lists are ordered deterministically.

### GET /api/session
- Returns an authentication summary with `auth`, `identity`, and `session` fields.
- Session ids are redacted; tokens are represented by fingerprints.
- Errors return deterministic guidance payloads with HTTP 401/403.

### POST /api/login
- Body: `{"username":"...","password":"..."}` or `{"identity": {...}}` when identity login is enabled.
- Optional: `issue_token` (boolean), `expires_in` (ticks).
- Response includes identity summary, session summary, optional token, and trace events.

### POST /api/logout
- Revokes the active session and clears the session cookie.
- Response includes session summary and a deterministic revocation trace.

### POST /api/action
- Body: `{"id": "<action id>", "payload": {}}` with `Content-Type: application/json`.
- Response mirrors the existing action response schema: `ok`, `state` snapshot, `revision`, and optional `overlay` and `error` keys for failures.
- Errors are deterministic engine payloads; invalid bodies return an engine error payload with HTTP 400.

### POST /api/upload
- Accepts multipart form data or chunked upload bodies.
- Stores uploads under the scoped runtime store and returns deterministic metadata.
- Response includes `ok`, `upload`, and `traces` (state, progress, preview, received, stored).
- `upload` includes `state`, `progress`, and `preview` metadata:
  - `state`: `accepted`, `receiving`, `validated`, `rejected`, `stored`
  - `progress`: `bytes_received`, `total_bytes`, `percent_complete`
  - `preview`: `filename`, `content_type`, `size`, `checksum`, plus `page_count` or `item_count` when available
- Errors return `ok: false` with `upload.state: rejected` and `upload.error` including `code`, `reason`, and `recovery_actions`.

### GET /api/uploads
- Returns `{"ok": true, "uploads": [...]}` with deterministic ordering.
- Upload entries include logical name, size, checksum, scoped stored path, plus `state`, `progress`, and `preview` metadata.

### GET /api/logs
- Returns `{"ok": true, "count": <number>, "logs": [...]}` with deterministic ordering.
- Logs are structured events with stable ids, levels, messages, optional fields, and event schema keys (event_kind, scope, outcome, identifiers, payload, order).

### GET /api/traces
- Returns `{"ok": true, "count": <number>, "spans": [...]}` with deterministic ordering.
- Spans include stable ids, names, parent relationships, status, and step ranges.

### GET /api/trace
- Compatibility alias for `/api/traces`.

### GET /api/metrics
- Returns `{"ok": true, "counters": [...], "timings": [...], "summary": {...}}` with deterministic ordering.
- Counters and timings include stable labels and step-based timing data.

### GET /api/build
- Returns build summaries for each target, including build id, location, and entry instructions.
- Ordering is deterministic; no host paths or secrets appear.

### GET /api/deploy
- Returns deployment state, including active build, last ship, and rollback availability.
- Includes a redacted environment summary with required vs optional keys and guidance.

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
