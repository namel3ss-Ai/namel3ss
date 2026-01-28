# Contributing to namel3ss

Clarity beats cleverness. Every change should make the language easier to understand, safer to run, and more enjoyable to use.

---

## Non-Negotiables

1) 500-Line Rule  
- Hard cap: every file stays under 500 LOC.  
- Split near ~400 LOC. If a file grows, turn it into a folder module.

2) Single Responsibility  
- One file does one job. If it starts doing two, split it — even at 150 lines.

3) Folder-First Naming  
- Prefer folders over filename prefixes.  
  - ✅ `parser/statements/control_flow.py`  
  - ❌ `parser_statements_control_flow.py`

4) Tests Mirror Source  
- If you change `src/namel3ss/<area>/`, add or update tests under `tests/<area>/`.

5) Package Safety  
- Packages must ship `capsule.ai` with explicit exports.  
- LICENSE + checksums are required; no install scripts or hooks.  
- Run `n3 pkg validate`, `n3 test`, and `n3 verify --prod` where applicable.

6) `.ai` Is the Extension  
- Examples and templates use `.ai` only. Do not add `.n3` or other extensions.

---

## Contributing to Official Capability Packs

- Official packs live under `packs/official/`.
- Packs are integrated via `pack.yaml`, `capabilities.yaml`, `intent.md`, and signing (where applicable).
- Tools must not be registered via Python runtime hooks or side effects.
- Official packs must not introduce third-party dependencies (standard library only).
- Prefer extending existing official packs instead of creating overlapping ones. Example: extend `packs/official/http` rather than introducing a new HTTP/web pack.
- Write-enabled capabilities (POST / PUT / DELETE) introduce side effects, require stronger governance, and should live in a separate, explicitly governed pack; do not add them casually to existing read-only packs.

---

## Expectations for Every Change

- Keep behavior stable unless a change is explicitly required. Preserve public imports and facades.  
- Memory imports outside the memory subsystem must go through `namel3ss.runtime.memory.api` or `namel3ss.runtime.memory.types`.  
- Errors must be clear, actionable, and include line/column when possible (use caret rendering where applicable).  
- Determinism first: AI is the only non-deterministic boundary, and it must stay explicit.

---

## Development Setup

Install in editable mode:
```bash
pip install -e .
```

Run tests:
```bash
python -m pytest -q
```

Compile check:
```bash
python -m compileall src -q
```

Memory import guard:
```bash
python3 tools/memory_import_guard.py
```

Enforce line limit:
```bash
python tools/line_limit_check.py
```

Formatting and linting for `.ai`:
```bash
n3 <your_app.ai> format
n3 <your_app.ai> lint
```

If you change language/engine/parsing, update examples and integration tests accordingly.

### Repository map
- `src/namel3ss/` — runtime, parser, validators, UI manifest generation.
- `tests/` — mirrors source structure; contract/grammar guards live here.
- `docs/language/grammar_contract.md` — frozen grammar/semantics (do not change without RFC).
- `docs/language/backward_compatibility.md` — policy for breaking/compatible changes.
- `docs/language/rfc_process.md` — when/how to propose breaking or semantic changes.
- `src/namel3ss/templates/` — onboarding surfaces; must pass STATIC validation.

Quick reminders:
- File size: ≤500 LOC; split near 400 with folder-first naming.
- Single responsibility per file.
- Propose grammar/UI changes as small PRs with examples and tests.

---

## Grammar and RFC boundaries
- The grammar and semantics are frozen; see `docs/language/grammar_contract.md`.
- Backward compatibility rules are in `docs/language/backward_compatibility.md`.
- Grammar, syntax, semantic, or validation-mode changes require an RFC (`docs/language/rfc_process.md`) before code changes.
- Most contributions should not touch the parser or grammar tables; prefer adding tests, diagnostics, or docs.

To add validators/UI elements/tools:
- Add source under the appropriate `src/namel3ss/<area>/` folder.
- Add focused tests under `tests/<area>/`.
- Keep Studio/CLI parity and STATIC validation behavior unchanged.

---

## What to Work On
- Fix bugs with clear reproduction tests.  
- Improve error messages.  
- Add or strengthen tests and coverage.  
- Improve documentation.  
- Improve Studio UX without weakening language authority.  
- Improve packaging/install reliability.  
- Provider improvements (stable and tested).

## What Not to Do (Without Discussion)
- Grammar changes or new syntax sugar.  
- Breaking changes.  
- Big architectural refactors.  
- Adding providers beyond Tier-1.  
- Feature bloat (styling DSL, GraphQL, distributed engine).

---

## Commit Style
- Use clear, scoped messages:  
  - `parser: enforce block-only buttons`  
  - `engine(ai): add provider registry`  
  - `studio: add /api/action endpoint`  
  - `docs: add quickstart`
- Keep commits small and descriptive.

---

## Pull Request Checklist
- Files remain under 500 LOC; single responsibility maintained.  
- Tests added/updated and `python -m pytest -q` passes.  
- `python tools/line_limit_check.py` passes.  
- Docs updated if behavior changed.  
- No unintended breaking changes.
- No grammar or semantic changes unless an approved RFC is linked.

---

## Philosophy
namel3ss is not trying to be everything. It must stay understandable, deterministic, and explicit about AI. If a feature makes namel3ss harder to learn, we don’t ship it — we redesign it.

---

## Before opening an issue

Thank you for contributing to namel3ss.

This repository uses **GitHub Issue Forms** to keep issues focused and actionable.
When opening an issue, please select the appropriate form provided by GitHub:

- **Bug report** — concrete defects with a minimal reproduction  
  https://github.com/namel3ss-Ai/namel3ss/issues/new?template=bug.yml

- **Documentation improvement** — small, scoped doc fixes or clarifications  
  https://github.com/namel3ss-Ai/namel3ss/issues/new?template=docs.yml

- **Tests / Regression coverage** — test-only additions to lock existing behavior  
  https://github.com/namel3ss-Ai/namel3ss/issues/new?template=tests.yml

- **Developer experience (DX)** — small polish to messages, help output, or UX  
  https://github.com/namel3ss-Ai/namel3ss/issues/new?template=dx.yml

Issues opened outside these forms may be closed or redirected.

For language design proposals, new syntax ideas, architectural discussions, or
open-ended questions, please use **Discussions** instead.

### What issues are for
Issues are used to track **concrete, actionable work**, such as:
- Bugs with a clear reproduction
- Small, scoped improvements
- Missing tests
- Documentation clarifications
- Developer experience polish

Each issue should be solvable without redesigning the language.

### What issues are NOT for
Please do NOT open issues for:
- Language design proposals
- New syntax ideas
- Architectural changes
- Feature brainstorming
- Open-ended discussions

### Scope expectations
A good issue should:
- Be focused on one thing
- Be solvable in a few hours
- Touch a small number of files
- Have a clear definition of “done”

If an issue requires design debate, it is probably not an issue.

### Title requirements
Issue titles must:
- Start with a verb (Fix / Add / Improve / Align / Clarify)
- Describe a concrete action
- Avoid questions or speculative language

### Roadmap relationship
The roadmap describes the **future shape of the language**.
Issues describe **work that may or may not contribute to that future**.

Opening an issue does not imply roadmap inclusion.

### Maintainer discretion
Maintainers may close issues that are out of scope, ask to move topics to
Discussions, or narrow issues for clarity. This is intentional and helps keep
the project focused.

Thank you for helping build namel3ss.
