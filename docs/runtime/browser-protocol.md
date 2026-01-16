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
- Returns `{"ok": true, "state": {...}, "revision": "<hash>"}` when the program loads.
- If load fails, returns `{"ok": false, "error": {...}, "revision": "<hash>"}`.

### POST /api/action
- Body: `{"id": "<action id>", "payload": {}}` with `Content-Type: application/json`.
- Response mirrors the existing action response schema: `ok`, `state` snapshot, `revision`, and optional `overlay` and `error` keys for failures.
- Errors are deterministic engine payloads; invalid bodies return an engine error payload with HTTP 400.

### GET /api/health
- Returns `{"ok": true, "status": "ready", "mode": "<run|dev|preview>"}` with no timestamps.

## Determinism guarantees
- Ports start at 7340 and increment deterministically when occupied.
- Revisions derive from source content hashing; identical sources yield identical revisions.
- JSON serialization is canonical and ordered; no timestamps, host paths, or random ids appear in payloads.
- Runtime artifacts remain under `.namel3ss/` and are ignored by git; running the server must not dirty the repo.

## UI shell
- `/` serves the runtime HTML shell that pulls `/api/ui` and `/api/state` and triggers `/api/action`.
- The shell is shared by run/preview; Studio uses a separate UI.
