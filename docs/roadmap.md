# namel3ss Roadmap

namel3ss is an English-first, AI-native, full-stack programming language, built from the ground up to support AI. This roadmap shows what is **done**, what is **next**, and what is intentionally **out of scope** until real users demand it.

---

## Guiding Principles (Locked)

- **English-first, strict grammar** (no free-form English)
- **AI is explicit, inspectable, and bounded**
- **Deterministic engine** (AI is the only non-deterministic boundary)
- **Full-stack in one language** (UI + backend + AI)
- **Discipline is non-negotiable**
  - `< 500 LOC` per file (split at ~400)
  - single responsibility per file
  - folder-first structure
  - tests mirror `src/`
  - `.ai` is the only source file extension

---

## ✅ Completed (v0.1.0-alpha)

### Phase 0 — Foundation & Discipline ✅
- Repo structure (`src/`, `tests/`, `docs/`)
- CI checks + line-limit enforcement
- CONTRIBUTING rules (single responsibility, 500 LOC)
- Consistent test layout

### Phase 1 — Core Language Spine ✅
- Lexer → Parser → AST → IR → Runtime pipeline
- Variables: `let`, `set`, `constant`
- Expressions, comparisons, boolean logic
- Human-readable errors (line/column)

### Phase 2 — Control Flow ✅
- `if / else`
- `repeat` / `for each`
- `match / when / otherwise`
- `try / catch`
- `return`

### Phase 3 — Records + Validation + In-Memory Persistence ✅
- `record` schema definitions
- Constraints: `present`, `unique`, `pattern`, `gt/lt`, length variants
- Runtime `save` / `find`
- Structured validation errors

### Phase 4 — Full-Stack UI (WOW loop) ✅
- Declarative `page` blocks
- Auto forms + tables from records
- Deterministic action IDs
- UI actions: `call_flow`, `submit_form`
- Table previews from store
- Block-only button grammar enforced

### Phase 5 — AI Core (Structured & Traceable) ✅
- `ai` profiles with model + system prompt
- `ask ai ... with input: ... as ...` (locked form)
- Tool exposure and tool loop guardrails (mock tool calls)
- Memory v1: short-term / semantic / profile
- Full AI traces (inputs/outputs/memory/tools)

### Phase 6 — Multi-Agent Orchestration v1 ✅
- `agent` declarations (AI + system prompt)
- `run agent ... as ...`
- `run agents in parallel: ... as ...`
- Guardrails + deterministic parallel trace wrapper
- Memory integration for agents

### Phase 7 — Toolchain (CLI + Formatter + Linter) ✅
- File-first CLI:
  - `n3 app.ai`
  - `check`, `ui`, `actions`, `flow`, `format`, `lint`, `studio`
- Deterministic formatter (`format`, `format check`)
- Linter (`lint`, `lint check`) with JSON findings
- Actions listing (`actions`, `actions json`)
- Caret-based error rendering

### Phase 8 — Studio v1 ✅
- Studio viewer (`studio`)
- Interactor: click buttons, submit forms, persistent session state/store
- Panels: UI, Actions, State, Traces, Lint
- Safe edits v1 (title/text/button rename) with round-trip:
  - edit → format → parse → lower → write (or reject)

### Phase 9 — Demos + Quickstart ✅
- 3 flagship examples:
  - CRUD dashboard
  - AI assistant over records
  - Multi-agent workflow
- Quickstart guide
- Integration smoke tests to keep examples alive

### Phase 10 — Templates (`n3 new`) ✅
- `n3 new crud | ai-assistant | multi-agent`
- Packaged templates with placeholders
- Generated apps are formatted + lint-clean
- `.gitignore` includes `.env` by default

### Phase 11 — Release & Packaging ✅
- `0.1.0-alpha` versioning
- `VERSION` + `CHANGELOG.md`
- Package ships templates + Studio web assets
- Release smoke test (scaffold + parse/lower)

### Phase 12 — Providers + Secrets UX ✅
- Provider field in AI profiles (default `mock`)
- Provider registry + engine selection
- Tier-1 providers implemented:
  - Ollama, OpenAI, Anthropic, Gemini, Mistral
- Config system (env/file/default)
- `.env` auto-loading next to `app.ai` (env vars override `.env`)
- Friendly missing-key errors
- Comprehensive provider/config tests

### Phase 13 — Persistence v1 (SQLite) ✅
Goal: records survive restarts.
- SQLite-backed store
- minimal migrations story
- preserve structured validation errors
- Studio/CLI support remains unchanged

---

## ✅ Phase 14 — Spec Freeze + Executable Spec + Invariant CI
Goal: freeze v1 contracts and prevent regressions.
- Canonical spec version map (single source of truth)
- Executable spec suite with snapshots + golden failures
- Invariant catalog (pass + fail fixtures)
- CI enforcement for legacy syntax, trace schema keys, and error stability

---

## ⏱️ Now (Phase 15)

### Phase 15 — Extraordinary Pack Authoring + Publishing (Local-First, Trust-First)
Goal: make pack authoring and publishing explicit, explainable, and local-first.
- Pack init/review/validate/bundle/sign workflows
- Capabilities declarations and review surfaces
- Deterministic bundling and trust metadata
- Installed pack status with source + capability summary

---

## 🔜 Next (post v0.1.0-alpha)

The next phases are intentionally based on real user demand. We do not ship “big features” without real usage pressure.

### Phase 16 — Tool Calling for Tier-1 Providers
Goal: feature parity with real providers.
- OpenAI tool calling
- Anthropic tool calling
- Gemini tool calling
- Mistral tool calling
- unified tool-call trace shape

### Phase 17 — Auth & Users (Minimal)
Goal: enable per-user apps and meaningful memory scopes.
- `record "User"` conventions
- login/logout flows
- `state.user` consistency
- simple guard: “require user”

### Phase 18 — Standard Library v1
Goal: small, deterministic helpers (no bloat).
- `time.*`, `math.*`, `string.*`, `json.*`
- deterministic, testable utilities only

---

## 🚫 Intentionally Out of Scope (until proven necessary)

These features can dilute focus and create chaos if added too early:

- UI styling DSL
- GraphQL
- Distributed agents
- Vendor-specific vector DB integrations
- “AI auto-code inside the language”

namel3ss stays powerful by staying understandable.

---

## Release philosophy

- **Alpha means honesty.**
- We ship fast, but we ship with discipline.
- If something is hard to learn, we redesign it.

The Rule of 3 applies:
> If you can’t grasp the basics in 3 minutes, we redesign it.
