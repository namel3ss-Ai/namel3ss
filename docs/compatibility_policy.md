# Compatibility Policy

Namel3ss uses semantic versioning and explicit compatibility classes.

## Versioning rules

- **Major**: breaking public API or behavior changes.
- **Minor**: backward-compatible feature additions.
- **Patch**: backward-compatible fixes.

## Public contract surface

The following are public contracts:

- grammar and parser behavior
- IR-to-manifest contract
- runtime action/state payload contracts
- plugin API allowlist
- documented CLI commands and flags

Public APIs are declared in `src/namel3ss/lang/public_api.py`.

## Agent contract compatibility

For agent runtimes, the canonical boundary contracts are compatibility-governed:

- `agent.route`
- `agent.retrieve`
- `agent.tool_policy`
- `agent.fallback`
- `agent.citations.format`
- `agent.answer`

Rules:

- field renames/removals are breaking
- field additions must be additive with deterministic defaults
- flow names remain stable across Starter, Controlled, and Full custom tiers

## Breaking change definition

A change is breaking if it:

- rejects previously valid source
- changes manifest/action schema in a non-additive way
- changes deterministic ordering or stable ID semantics
- removes or renames a public CLI command or documented flag
- removes plugin API methods without deprecation window

## Allowed in minor/patch releases

- additive fields with deterministic defaults
- clearer diagnostics with same failure class
- internal refactors that preserve outputs and contracts
- security fixes that do not alter public behavior unexpectedly

## Enforcement

- compatibility tests run in CI
- deprecations are warned before removal
- release checklist verifies compatibility docs and changelog alignment

## Studio and production parity

- Studio may expose extra diagnostics panels
- Public runtime behavior must remain contract-compatible with Studio-disabled mode
- Studio-only features are documented explicitly
