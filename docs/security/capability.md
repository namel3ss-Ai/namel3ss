# Capability Contract

Capabilities are enforced as negative guarantees and explicit policy permissions. Policy and overrides can only restrict; they never expand guarantees.

## Ingestion policy actions
- ingestion.run (allowed when policy block is omitted)
- ingestion.review (allowed when policy block is omitted)
- ingestion.override (requires explicit permission)
- ingestion.skip (requires explicit permission)
- upload.replace (requires explicit permission)

See docs/runtime/ingestion.md for the full policy contract.

## Retrieval policy actions
- retrieval.include_warn (requires explicit permission)

Retrieval results always exclude blocked content, even when warnings are allowed.
See docs/runtime/retrieval.md for details.

## Tool capabilities
- filesystem_read
- filesystem_write
- network
- subprocess
- env_read
- env_write
- secrets

Tool guarantees are derived from pack capabilities, tool purity, app overrides, and trust policy. Denied tool calls emit capability_check traces.
See docs/capabilities.md and docs/trace-schema.md.

## Jobs and scheduling
- jobs
- scheduling

Apps must declare required backend capabilities in app.ai. Missing declarations are rejected at compile time.
See docs/language/backend-capabilities.md.

## Explain visibility
Denied operations emit capability_check traces or policy errors with deterministic reason codes and guidance.
