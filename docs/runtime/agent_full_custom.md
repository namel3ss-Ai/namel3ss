# Full Custom Agents

This guide defines the full custom (`100+` lines) path for namel3ss agents.

## Scope

Use this mode when you need:

- explicit multi-agent orchestration
- custom memory behavior
- custom tool policy and approval gates
- custom fallback and citation formatting

Unlike Starter and Controlled, this mode does not require `use preset`.

## Contract boundaries

Keep these canonical flow boundaries stable:

- `agent.route`
- `agent.retrieve`
- `agent.tool_policy`
- `agent.fallback`
- `agent.citations.format`
- `agent.answer`

You may add extra orchestration flows (for example `agent.plan`) as long as canonical boundaries remain compatible.

## Advanced runtime controls

### Memory

- define explicit AI memory settings per profile (`short_term`, `semantic`, `profile`)
- keep deterministic persistence behavior explicit in flows

### Tools and policy

- gate tool usage in `agent.tool_policy`
- return deterministic denial reasons for blocked tools

### Sandbox and approvals

- route risky operations through explicit policy flows
- keep approvals as deterministic decisions in flow outputs

## Migration from other tiers

1. Start from Starter ([`apps/agent-workspace-starter/app.ai`](https://github.com/namel3ss-Ai/namel3ss-apps/tree/main/apps/agent-workspace-starter)).
2. Move to Controlled ([`apps/agent-workspace-controlled/app.ai`](https://github.com/namel3ss-Ai/namel3ss-apps/tree/main/apps/agent-workspace-controlled)) by overriding specific flows.
3. Move to Full custom ([`apps/agent-workspace-full-custom/app.ai`](https://github.com/namel3ss-Ai/namel3ss-apps/tree/main/apps/agent-workspace-full-custom)) by removing preset dependency and declaring contracts/flows directly.

## Determinism checklist

- contract names and field order are stable
- fallback behavior is deterministic for empty context and provider errors
- `n3 expand` output is inspectable
- traces clearly show orchestration flow calls
