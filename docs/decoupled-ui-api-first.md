# Decoupled UI API-First Architecture

This phase adds a headless runtime mode and stable UI API contracts so front-ends can be hosted and scaled separately from the namel3ss runtime.

## What is new

- Versioned headless endpoints:
  - `GET /api/v1/ui`
  - `POST /api/v1/actions/<action_id>`
- API-first endpoints for runtime UI contracts:
  - `GET /api/ui/manifest`
  - `GET /api/ui/state`
  - `GET /api/ui/actions`
  - `POST /api/ui/action`
- Headless runtime mode for `n3 run`, `n3 dev`, `n3 preview`, and `n3 start`.
- Deterministic UI bundle export:
  - `n3 app.ai ui bundle --out <dir>`
- Front-end client package scaffold:
  - `packages/namel3ss-ui-client`

## Runtime contracts

All API-first responses include `api_version`, `contract_version`, and deterministic field ordering.

Headless `v1` responses include:

- `manifest` (existing UI manifest payload)
- `hash` (`sha256` of canonical manifest JSON)
- optional `state` and `actions` when `include_state=1` / `include_actions=1` are set
- optional `runtime_error` and `runtime_errors`
- optional `contract_warnings` in Studio/dev when runtime validation detects schema drift
- OpenAPI reference: `docs/headless-api-openapi.json`

Contract version:

- `contract_version: "runtime-ui@1"`
- Version changes only on breaking schema changes.

- `UIManifest`
  - `manifest.pages`
  - `manifest.flows`
  - `manifest.components`
  - `theme`
- `UIState`
  - `state.current_page`
  - `state.values`
  - `state.errors`
- `ActionResult`
  - `success`
  - `new_state`
  - `message`

## Headless mode

Use `--headless` to disable static UI hosting while keeping API endpoints available.

Examples:

- `n3 run --headless --api-token dev-secret --cors-origin https://frontend.example.com`
- `n3 dev --headless`
- `n3 preview --headless`
- `n3 start --headless`

When headless mode is enabled, `/` returns `404` and UI clients should call API endpoints directly.
`/api/v1/*` requires the configured token (`X-API-Token` header or `Authorization: Bearer ...`).

## Static UI bundle

`n3 app.ai ui bundle --out dist/ui` writes a deterministic bundle:

- `index.html`
- `runtime.js`
- `runtime.css`
- `ui_manifest.json`
- `ui_actions.json`
- `ui_state.json`
- `ui_schema.json`
- `bundle_manifest.json`

`bundle_manifest.json` contains deterministic file hashes.

## Front-end package

`packages/namel3ss-ui-client/src/index.js` provides a tiny compatibility client with:

- `getManifest()`
- `getState()`
- `getActions()`
- `runAction(id, payload)`

Official strict SDK:

- `packages/namel3ss-client`
- package name: `@namel3ss/client`
- typed payloads for UI, actions, runtime errors, and ingestion/RAG state
- contract validation backed by runtime-generated schema (`runtime_contract_schema.json`)
