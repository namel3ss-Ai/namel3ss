# Agent Contracts

This document defines the canonical flow contracts for deterministic agent apps.

Use these contracts for:

- Starter preset expansion (`use preset "agent_workspace"`)
- Controlled mode overrides (`~50` lines)
- Full custom agent graphs (`100+` lines)

## Canonical flow contracts

### `agent.route`

Input:

- `message: text`
- `context: optional text`

Output:

- `route: text`
- `query: text`
- `context: text`

### `agent.retrieve`

Input:

- `query: text`
- `context: optional text`

Output:

- `context: text`
- `citations: json`

### `agent.tool_policy`

Input:

- `tool_name: text`

Output:

- `allowed: boolean`
- `reason: text`

### `agent.fallback`

Input:

- `message: text`
- `context: optional text`
- `error_text: optional text`

Output:

- `answer_text: text`
- `citations: json`

### `agent.citations.format`

Input:

- `citations: json`

Output:

- `citations: json`

### `agent.answer`

Input:

- `message: text`
- `context: optional text`

Output:

- `answer_text: text`
- `citations: json`

## Determinism requirements

- Flow names and field names are stable and case-sensitive.
- Contract field order is deterministic and must not be randomized.
- `n3 expand` must produce reproducible generated contracts for identical source.
- New fields must be additive unless a contract version change is declared.

## Usage guidance by tier

Starter (`<=10` lines):

- rely on preset defaults and generated contracts

Controlled (`~50` lines):

- keep contract names stable
- override internals, not contract shape

Supported controlled overrides for `use preset "agent_workspace"`:

- `override flow "agent.route"`
- `override flow "agent.retrieve"`
- `override flow "agent.answer"`
- `override flow "agent.tool_policy"`
- `override flow "agent.fallback"`
- `override flow "agent.citations.format"`

Override precedence is deterministic:

1. If a supported flow is overridden, the override body is emitted.
2. If a flow is not overridden, the preset default body is emitted.
3. Contract signatures stay canonical in both cases.

Full custom (`100+` lines):

- compose custom flow graphs while preserving canonical boundary contracts

Reference examples (canonical in `namel3ss-apps`):

- Starter: [`apps/agent-workspace-starter/app.ai`](https://github.com/namel3ss-Ai/namel3ss-apps/tree/main/apps/agent-workspace-starter)
- Controlled: [`apps/agent-workspace-controlled/app.ai`](https://github.com/namel3ss-Ai/namel3ss-apps/tree/main/apps/agent-workspace-controlled)
- Full custom: [`apps/agent-workspace-full-custom/app.ai`](https://github.com/namel3ss-Ai/namel3ss-apps/tree/main/apps/agent-workspace-full-custom)

Related:

- `docs/runtime/agent_full_custom.md`
