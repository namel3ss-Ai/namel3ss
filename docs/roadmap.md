---
# namel3ss Roadmap

## Roadmap intent

This roadmap describes the intended shape of the language, not a backlog.
Execution is demand-driven by real application needs and demonstrated evidence.
Determinism and trust are non-negotiable; the AI boundary stays explicit and inspectable.
Alpha honesty applies: the current release is v0.1.0a7.

## Guiding principles (locked)

- English-first, strict grammar (no free-form English)
- Explicit, inspectable AI boundary
- Deterministic engine; AI is the only non-deterministic boundary
- Full-stack in one language (UI + backend + AI)
- Discipline: < 500 LOC per file, single responsibility, folder-first, tests mirror `src/`, `.ai` only

## Established foundation (<= v0.1.0a7)

By v0.1.0a7, the language spine (lexer -> parser -> AST -> IR -> runtime) and deterministic execution are stable, with the UI DSL for full-stack apps. The AI boundary is explicit with traces and memory, plus agent orchestration, and the CLI toolchain covers run, format, lint, and actions. Studio provides interactive inspection and safe edits; templates and packaging ship with the distribution; spec contracts are frozen with executable invariants and CI enforcement.

## Active focus (v0.1.x)

Pack authoring and publishing stays local-first and trust-first, with explicit init/review/validate/bundle steps. Capabilities are declared in packs and exposed through review surfaces. Bundling is deterministic and produces signed artifacts; verification is enforced on install. Install status surfaces show source, capabilities, and verification state.

Not included: hidden magic, AI auto-code inside the language, or any pack install path that skips capability review.

## Future direction (demand-driven)

- Provider-agnostic tool invocation with a consistent tool-call trace shape across providers.
- Minimal explicit user identity and scoped state/memory, only when real apps demand it.
- Small deterministic standard library, clarity-first and no bloat.
- Studio trust surfaces and explainability UX deepen as inspection needs grow.

## Intentionally out of scope (until proven necessary)

- UI styling DSL
- GraphQL
- Distributed agents
- Vendor-specific vector DB integrations
- AI auto-code inside the language

## Contribution note

Issues and concrete use cases are welcome.
The roadmap is steward-owned; changes are deliberate and rare.
---
