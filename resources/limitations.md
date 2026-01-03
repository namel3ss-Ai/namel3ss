# namel3ss - Limitations (v0.1.0a6)

This document lists current limitations and boundaries based on runtime, CLI, Studio behavior, and enforced tests. It is not a roadmap.

## Hard Limitations (Current)

- Execution is single-process and local; there is no distributed runtime, clustering, or multi-host scheduler.
- Studio runs as a local HTTP server bound to 127.0.0.1 with per-process session state; there is no multi-user or shared-session mode.
- Spec versions are enforced: programs must declare a spec and only `1.0` is supported; unsupported specs fail before execution.
- Spec migration support is limited to declared paths (currently `0.9` -> `1.0`); other migrations are rejected.
- Persistence is opt-in: default is in-memory; sqlite and postgres are supported via `N3_PERSIST`/`N3_PERSIST_TARGET`; the `edge` target is not implemented.
- AI provider features are limited: streaming and JSON mode are not supported; each provider response yields at most one tool call; `ollama` has no tool calling.

## Intentional Constraints

- UI components are limited to the built-in set: title, text, form, table, button, section, card, and layout (row/column).
- Theme control is limited to light/dark/system plus optional theme tokens; arbitrary CSS or layout styling is not supported.
- Canonical types are required; legacy aliases are accepted but linted as errors by default and rewritten by the formatter.
- Built-in tool packs are intentionally small (`text`, `math`, `datetime`, `file`, `http`); non-trivial behavior must be implemented as tools.
- App-defined tools require explicit bindings in `.namel3ss/tools.yaml`.

## Security & Safety Boundaries

- Sensitive operations (filesystem, network, env, subprocess, secrets) are gated by capabilities; access is denied unless explicitly allowed.
- Secret values are never persisted; only secret access metadata is logged to `.namel3ss/secret_audit.jsonl` when auditing is enabled.
- Local artifacts are written per run when a project root is available: `.namel3ss/execution/last.json`, `.namel3ss/tools/last.json`, and `.namel3ss/memory/memory_snapshot.json`.

## Non-Goals

- No built-in authentication, roles, or user-management system.
- Not a general-purpose programming language or web framework.
- No native mobile or desktop packaging/installer output.

## Known Edge Cases

- Determinism guarantees apply to canonicalization and hashing; external providers or tools that depend on time/network can produce different outcomes across runs.
- Studio page navigation is a simple page selector; there is no URL routing or deep-linking.

## What Is Explicitly Not Supported

- Streaming responses or provider JSON mode.
- Multiple tool calls in a single provider response.
- Edge persistence target.
- Public registry hosting or automatic background updates.
- Remote Studio hosting or multi-tenant Studio sessions.

## Future Work (Not Promised)

- Frequently requested but not implemented: public registry hosting, streaming/JSON-mode providers, distributed execution, richer UI theming.
