# Headless Contracts

Namel3ss headless endpoints expose a strict, versioned runtime contract for integrations.

## Contract version

- `contract_version` is emitted in all `/api/v1/*` responses.
- Current value: `runtime-ui@1`.
- Breaking changes require a new contract version.
- Additive fields do not change the version.

## Endpoints

- `GET /api/v1/ui`
  - Optional query:
    - `include_state=1`
    - `include_actions=1`
- `POST /api/v1/actions/<action_id>`
  - Body shape:
    - `{ "args": { ... } }`

## Core response fields

All headless payloads include:

- `ok: boolean`
- `api_version: "v1"`
- `contract_version: "runtime-ui@1"`

UI payloads include:

- `manifest` (deterministic UI manifest)
- `hash` (sha256 over canonical manifest JSON)
- optional `state`
- optional `actions`

Action payloads include:

- `action_id`
- optional `state`
- optional `manifest`
- optional `result`

Retrieval/answer payloads may include additive deterministic evidence fields:

- `retrieval_plan`
- `retrieval_trace`
- `trust_score_details`

Error and diagnostics fields:

- `runtime_error` (primary)
- `runtime_errors` (ordered diagnostics)
- `contract_warnings` (dev/studio schema warnings; non-blocking)

## Validation behavior

- Runtime validates outgoing contract payloads in Studio/dev mode.
- Validation is non-blocking and never mutates payloads.
- Violations are surfaced via `contract_warnings`.

## Official SDK

`@namel3ss/client` consumes the same contract source used by runtime validation.

SDK guarantees:

- No hidden retries
- No hidden state
- Typed runtime errors
- Deterministic schema validation on parsed responses
