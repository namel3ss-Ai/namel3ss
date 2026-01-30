# Threat Model: Orchestration and Tools

## Assets
- Tool declarations and bindings
- Capability guarantees and policy overrides
- Job records and execution traces
- Input and output summaries for tool calls

## Trust Boundaries
- Flow execution -> tool runner (local, service, container)
- Job scheduler -> execution worker
- Pack metadata -> runtime enforcement

## Threat Classes
- Bypass
- Confusion
- Disclosure
- Injection
- Spoofing
- Tampering

## Mitigations
- Capability enforcement and policy restrictions (docs/capabilities.md, docs/language/backend-capabilities.md)
- Tool schema validation for inputs and outputs (docs/security/tool-validation.md)
- Trace schema for tool calls and capability checks (docs/trace-schema.md)
- Deterministic observability outputs and redaction (docs/observability.md)
- Pack review and trust policy gates (docs/trust-and-governance.md, docs/tool-packs.md)
