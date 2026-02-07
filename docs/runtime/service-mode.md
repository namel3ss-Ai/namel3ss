# Service Mode

Service mode runs a namel3ss app as a long-lived HTTP process with deterministic per-session state.

## Capability requirements
- `service`: required for any service run (`n3 serve`, `n3 run --service`)
- `multi_user`: required to create more than one concurrent session
- `remote_studio`: required to read remote Studio state/traces endpoints

Example:
```ai
capabilities:
  service
  multi_user
  remote_studio
```

## Run commands
- `n3 serve app.ai --port 8787`
- `n3 run app.ai --service --port 8787`

Both commands now enforce `service` capability identically.

## Session lifecycle
- Create: `POST /api/service/sessions` (optional role in payload)
- List: `GET /api/service/sessions` or `n3 session list`
- Kill: `DELETE /api/service/sessions/<session_id>` or `n3 session kill <session_id>`
- Idle cleanup uses `N3_SERVICE_IDLE_TIMEOUT_SECONDS` (defaults to 1800 seconds)

Session ids are deterministic (`s000001`, `s000002`, ...). State is isolated per session unless records are declared `shared`.

## Roles
Request role can be provided through header/payload and resolves to:
- `guest`
- `user`
- `admin`

Flows can read `session.role` for authorization checks.

## Remote Studio
- Connect with `n3 studio connect <session_id> --host <host> --port <port>`
- State endpoint: `/api/service/studio/<session_id>/state`
- Trace endpoint: `/api/service/studio/<session_id>/traces`

Without `remote_studio`, these endpoints return `403`.

## Security notes
- Service mode does not enable arbitrary code execution.
- Session ids and roles are validated before routing requests.
- Remote Studio endpoints are read-only and never mutate session state.
