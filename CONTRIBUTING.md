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

5) `.ai` Is the Extension  
- Examples and templates use `.ai` only. Do not add `.n3` or other extensions.

---

## Expectations for Every Change

- Keep behavior stable unless a change is explicitly required. Preserve public imports and facades.  
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

Enforce line limit:
```bash
python tools/line_limit_check.py
```

Formatting and linting for `.ai`:
```bash
n3 <your_app.ai> format
n3 <your_app.ai> lint
```

If you change language/runtime/parsing, update examples and integration tests accordingly.

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
- Feature bloat (styling DSL, GraphQL, distributed runtime).

Open an issue first if unsure.

---

## Commit Style
- Use clear, scoped messages:  
  - `parser: enforce block-only buttons`  
  - `runtime(ai): add provider registry`  
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

---

## Philosophy
namel3ss is not trying to be everything. It must stay understandable, deterministic, and explicit about AI. If a feature makes namel3ss harder to learn, we don’t ship it — we redesign it.

---

## Where to Ask Questions
- GitHub Issues for bugs and feature requests.  
- GitHub Discussions (if enabled) for design and questions.

Thank you for helping build namel3ss.
