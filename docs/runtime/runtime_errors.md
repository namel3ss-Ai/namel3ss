# Runtime Error Surfacing

Runtime failures and runtime diagnostics are normalized into a stable, user-safe contract.

## Runtime error contract

Primary runtime error field:

```json
{
  "runtime_error": {
    "category": "provider_misconfigured",
    "message": "AI provider is misconfigured.",
    "hint": "Set the selected provider and required API key in configuration.",
    "origin": "provider",
    "stable_code": "runtime.provider_misconfigured"
  }
}
```

Optional additive diagnostics:

```json
{
  "runtime_errors": [
    {
      "category": "provider_misconfigured",
      "message": "AI provider is misconfigured.",
      "hint": "Set the selected provider and required API key in configuration.",
      "origin": "provider",
      "stable_code": "runtime.provider_misconfigured"
    },
    {
      "category": "provider_mock_active",
      "message": "OpenAI key detected but provider is set to mock. Real AI calls are not active.",
      "hint": "Set [answer].provider to a real provider or remove unused keys.",
      "origin": "provider",
      "stable_code": "runtime.provider_mock_active.openai"
    }
  ]
}
```

Rules:
- Every failed runtime response has exactly one primary `runtime_error`.
- Secondary diagnostics are optional and appear in `runtime_errors` after the primary entry.
- Ordering is deterministic and deduplicated by `stable_code`.
- Payloads are user-safe: no stack traces, bearer tokens, or provider secrets.

## Categories (closed set)

- `server_unavailable`
- `auth_invalid`
- `auth_missing`
- `provider_misconfigured`
- `provider_mock_active`
- `action_denied`
- `policy_denied`
- `upload_failed`
- `ingestion_failed`
- `runtime_internal`

## Provider guardrails

Provider diagnostics are deterministic functions of config and environment:

- Unknown provider name -> `provider_misconfigured`.
- Provider set to `mock` while real provider keys exist -> `provider_mock_active`.
- Real provider selected without required key -> `provider_misconfigured`.

Guardrails are surfaced as runtime diagnostics in Studio and action responses. They do not auto-switch providers.

## UI manifest element

When runtime diagnostics are present, runtime injects a `runtime_error` element into each page:

```json
{
  "type": "runtime_error",
  "category": "provider_mock_active",
  "message": "OpenAI key detected but provider is set to mock. Real AI calls are not active.",
  "hint": "Set [answer].provider to a real provider or remove unused keys.",
  "origin": "provider",
  "stable_code": "runtime.provider_mock_active.openai"
}
```

The Studio renderer shows category, message, hint, origin, and stable code. Configuration errors are shown as warnings; other runtime failures are shown as errors.

## Determinism guarantees

- Classification is rule-based; no heuristic randomness.
- Same failure signal -> same category, message/hint defaults, and stable code.
- No timestamps or random IDs in runtime error payloads.
- Provider diagnostics are stable for the same config + environment.
