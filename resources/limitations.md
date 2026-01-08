# namel3ss - Limitations (v0.1.0a7)

This document lists current limitations and boundaries based on runtime, CLI, Studio behavior, and enforced tests. It is not a roadmap.

## Hard Limitations (Current)

- Execution is single-process and local — no distributed runtime, clustering, or multi-host scheduler.
- Studio runs as a local HTTP server bound to 127.0.0.1 with per-process session state — no multi-user or shared-session mode.
- Spec versions are enforced; only `1.0` is supported — unsupported specs fail before execution.
- Spec migration support is limited to declared paths (`0.9` -> `1.0`) — other migrations are rejected.
- Persistence is opt-in; default is in-memory — sqlite and postgres are supported via `N3_PERSIST`/`N3_PERSIST_TARGET`, and `edge` is not implemented.
- AI provider features are limited — streaming and JSON mode are not supported; each provider response yields at most one tool call; `ollama` has no tool calling.

## Expression Language

- No lambdas or anonymous functions — keeps expressions explicit and traceable.
- No `=` assignment outside `calc:` — avoids implicit mutation in expressions.
- Expressions cannot perform language-level mutation (`set`, record writes, theme changes) — mutation remains statement-only.
- Precedence is fixed; `-2 ** 2` parses as `-(2 ** 2)` — consistent right-associative exponentiation.
- Object literals (`{}`) are not supported — maps must use `map:` blocks.

## List Operations

- Aggregations require numeric lists (booleans are rejected) — no implicit coercion.
- Aggregations error on empty lists — avoids hidden defaults.
- `map/filter/reduce` bodies are single expressions (no statements) — keeps evaluation explicit.
- `reduce` rejects tool calls in target/start/body — prevents side effects during reduction.

## calc Blocks

- `calc:` is flow-only — pages remain declarative.
- Each calc line is a single assignment — commas or multi-target lines are rejected.
- Targets must be local identifiers or `state.<path>` — `input.*` and arbitrary dotted targets are rejected.
- Duplicate local names in one `calc:` block are errors — avoids accidental overrides.

## Studio & Explainability

- Explain traces are emitted for `calc:` assignments only — avoids tracing every expression.
- Explain payloads are bounded and may truncate long lists — keeps output deterministic.
- Formula View is visual-only; copy returns canonical code — no source rewriting.
- `n3 see` output is bounded and marks UI-only behavior — keeps UI inspection deterministic.

## Runtime & Determinism

- Core evaluation is deterministic; no randomness or timestamps — nondeterminism requires explicit tools/providers.
- Trace payloads omit nondeterministic fields (timestamps, durations) — hash inputs are stable.
- UI manifests and exports are canonical and bounded; runtime-only UI data is stripped.

## CI & Surface Freeze

- Expression surface is enforced by `expr-check` in CI and release gates — changes must update contract fixtures/tests.
- UI DSL surface is frozen by spec — changes must update `docs/ui-dsl.md` and UI tests.

## Intentional Constraints

- UI components are limited to the built-in set: title, text, image, form, table, list, chart, button, section, card, card_group, tabs/tab, modal/drawer, chat elements, and layout (row/column/divider) — keeps the UI DSL small and stable.
- UI packs are static composition only; no parameters, conditionals, flows, tools, or records — avoids runtime drift.
- Theme control is limited to light/dark/system plus optional theme tokens — arbitrary CSS is not supported.
- Canonical types are required; legacy aliases are accepted but linted as errors by default and rewritten by the formatter — keeps type naming stable.
- Built-in tool packs are intentionally small (`text`, `math`, `datetime`, `file`, `http`) — non-trivial behavior still belongs in tools; list aggregations are built-in expressions.
- App-defined tools require explicit bindings in `.namel3ss/tools.yaml` — no implicit tool discovery.

## Security & Safety Boundaries

- Sensitive operations (filesystem, network, env, subprocess, secrets) are gated by capabilities — access is denied unless explicitly allowed.
- Secret values are never persisted — only secret access metadata is logged to `.namel3ss/secret_audit.jsonl` when auditing is enabled.
- Local artifacts are written per run when a project root is available — `.namel3ss/execution/last.json`, `.namel3ss/tools/last.json`, `.namel3ss/memory/memory_snapshot.json`.

## Non-Goals

- No built-in authentication, roles, or user-management system.
- Not a general-purpose programming language or web framework.
- No native mobile or desktop packaging/installer output.

## Known Edge Cases

- Determinism guarantees apply to canonicalization and hashing — external providers or tools that depend on time/network can produce different outcomes.
- Studio page navigation is a simple page selector — there is no URL routing or deep-linking.

## What Is Explicitly Not Supported

- Streaming responses or provider JSON mode.
- Multiple tool calls in a single provider response.
- Edge persistence target.
- Public registry hosting or automatic background updates.
- Remote Studio hosting or multi-tenant Studio sessions.

## Not a Limitation

- Expressions are not “restricted”; they are frozen and guarded by `expr-check` to prevent regressions.
- Math does not require tool packs; list aggregations are built-in expressions.
- Studio visualization does not change execution or hashes.
