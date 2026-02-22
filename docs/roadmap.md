---
# namel3ss Roadmap

## Roadmap intent

This roadmap describes the intended shape of the language, not a backlog.
Execution is demand-driven by real application needs and demonstrated evidence.
Determinism and trust are non-negotiable; the AI boundary stays explicit and inspectable.
Alpha honesty applies: the current release is v0.1.0a24.
This document is informational only and does not promise future features.

## Guiding principles (locked)

- English-first, strict grammar (no free-form English)
- Explicit, inspectable AI boundary
- Deterministic engine; AI is the only non-deterministic boundary
- Full-stack in one language (UI + backend + AI)
- Discipline: < 500 LOC per file, single responsibility, folder-first, tests mirror `src/`, `.ai` only

## Established foundation (<= v0.1.0a24)

By v0.1.0a24, the language spine (lexer -> parser -> AST -> IR -> runtime) and deterministic execution are stable, with the UI DSL for full-stack apps. The AI boundary is explicit with traces and memory, plus agent orchestration, and the CLI toolchain covers run, format, lint, and actions. Studio provides interactive inspection and safe edits; templates and packaging ship with the distribution; spec contracts are frozen with executable invariants and CI enforcement.

## Progressive agent depth (implemented)

The language now supports three production-ready agent tiers:

1. Starter (`<=10` lines)
2. Controlled (`~50` lines)
3. Full custom (`100+` lines)

Canonical examples are published in [`namel3ss-apps`](https://github.com/namel3ss-Ai/namel3ss-apps):

- Starter: [`apps/agent-workspace-starter`](https://github.com/namel3ss-Ai/namel3ss-apps/tree/main/apps/agent-workspace-starter)
- Controlled: [`apps/agent-workspace-controlled`](https://github.com/namel3ss-Ai/namel3ss-apps/tree/main/apps/agent-workspace-controlled)
- Full custom: [`apps/agent-workspace-full-custom`](https://github.com/namel3ss-Ai/namel3ss-apps/tree/main/apps/agent-workspace-full-custom)

Implementation guarantees:

- stable canonical contracts for `agent.route`, `agent.retrieve`, `agent.tool_policy`, `agent.fallback`, `agent.citations.format`, and `agent.answer`
- deterministic preset expansion with controlled override precedence
- CI gates covering line-count tiers and deterministic behavior across Starter/Controlled/Full custom

## Intentionally out of scope (current)

- UI styling DSL
- GraphQL
- Distributed agents
- Vendor-specific vector DB integrations
- AI auto-code inside the language

## Contribution note

Issues and concrete use cases are welcome.
The roadmap is steward-owned; changes are deliberate and rare.
---
