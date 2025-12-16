# Namel3ss

Namel3ss is an English-first, AI-native full-stack programming language that spans parser → AST → IR → runtime with deterministic defaults and explicit AI boundaries.

## Now / Next / Later
- Now: Phase 0 skeleton with docs, CI guardrails, and package scaffolding.
- Now: Core language contract captured for stable keywords and boundaries.
- Now: Editable install flow for local development and automation.
- Next: Lexer tokens, parser entrypoints, and AST node contracts.
- Next: Deterministic runtime shell with hooks for AI-augmented paths.
- Next: CLI stub for compile/run loops and ergonomic feedback.
- Later: IR lowering, optimizer passes, and reproducible execution traces.
- Later: Deterministic stdlib surface with sandboxed IO and tracing.
- Later: AI-augmented behaviors (prompted blocks, planners) gated and logged.
- Later: Performance profiling, caching, and correctness hardening toward v3.

## Getting Started
- Install editable package: `pip install -e .`
- Run tests: `python -m pytest -q`
- Compile check: `python -m compileall src -q`
- Enforce line limit: `python tools/line_limit_check.py`

## Repository Layout
- `src/namel3ss/`: language packages (lexer, parser, ast, ir, runtime, cli, errors, utils)
- `tests/`: pytest suite (add coverage for every feature)
- `docs/`: roadmap and language contracts
- `tools/`: repo-level utilities (line-limit enforcement)
- `.github/workflows/`: CI automation

## Development Notes
- Each source file must stay under 500 lines.
- One responsibility per file; if it grows, split into a folder with smaller modules.
- Prefer folder-first naming (e.g., `parser/core.py`, not `parser_core.py`).

### Migration note (buttons)
- Buttons are block-only (to avoid grammar chaos):
  ```
  button "Run":
    calls flow "demo"
  ```
- Old one-line form is rejected:
  ```
  button "Run" calls flow "demo"
  ```

## Docs
- [IR Reference](docs/ir.md)
- [Runtime Model](docs/runtime.md)
- [Error Reference](docs/errors.md)
- [Quickstart](docs/quickstart.md)
- [Roadmap](docs/roadmap.md)
