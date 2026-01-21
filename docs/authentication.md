# Authentication

Authentication connects identity to sessions and tokens without external dependencies. The runtime resolves identity deterministically and emits redacted traces that Studio can inspect.

## Identity model
Identity includes:
- subject: stable unique id
- roles: list of text
- permissions: list of text
- trust_level: text (still used by trust rules)

Identity values come from config or environment:
- `N3_IDENTITY_JSON` or `N3_IDENTITY_*`
- `namel3ss.toml` `[identity]` defaults

Existing `identity.role` checks continue to work. Roles and permissions normalize from `roles`, `role`, `permissions`, `permission`, `scopes`, or `scope`.

```ai
identity "user":
  field "subject" is text must be present
  field "roles" is json
  field "permissions" is json
  field "trust_level" is text must be present
  trust_level is one of ["guest", "member", "admin"]

flow "admin_report": requires has_role("admin")
```

## Sessions
- Sessions are server-side and stored in the configured persistence backend.
- Create via `POST /api/login`, read via `GET /api/session`, revoke via `POST /api/logout`.
- Session ids are never returned raw in JSON; only redacted values like `session:abc123...`.
- Expiration uses logical ticks (no wall-clock timestamps).

Authentication settings are provided by:
- `N3_AUTH_USERNAME`, `N3_AUTH_PASSWORD`
- `N3_AUTH_ALLOW_IDENTITY` for identity login
- `N3_AUTH_SIGNING_KEY` for bearer tokens
- `namel3ss.toml` `[authentication]` defaults

## Tokens
- Bearer tokens are accepted via `Authorization: Bearer <token>`.
- `POST /api/login` can issue a token when `issue_token` is true and a signing key is configured.
- Verification is deterministic with categories: `valid`, `expired`, `revoked`.
- Tokens are never stored in traces or logs; only fingerprints like `token:abc123...`.

## Identity resolution order
1. Session cookie `n3_session`
2. Bearer token
3. Config identity defaults

## Guards and helpers
Use built-in predicates in requires clauses:
- `has_role("admin")`
- `has_permission("reports.view")`

Existing checks like `identity.role is "admin"` continue to work.

## Determinism and redaction
- JSON payloads are canonical and ordered.
- Session ids and tokens are redacted in traces, logs, and artifacts.
- No host paths, raw secrets, or wall-clock timestamps appear in stable outputs.
