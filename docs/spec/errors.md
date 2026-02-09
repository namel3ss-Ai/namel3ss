# Runtime Errors Specification

## Canonical Taxonomy
Runtime errors use a closed category set:
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

## Required Fields
Each normalized runtime error **must** include:
- `category`
- `message`
- `hint`
- `origin`
- `stable_code`

## Safety Rules
- Messages **must** be user-safe.
- Secrets and raw stack traces **must not** be exposed.
- Classification **must** be deterministic for equivalent failures.
