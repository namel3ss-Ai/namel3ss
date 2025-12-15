# Contributing to Namel3ss

We are building an English-first, AI-native language with deterministic defaults. Keep changes small, reviewable, and explicit.

## Core Rules
- **500-line limit:** Any `src/**/*.py` file must stay under 500 lines (CI enforced). Split files early.
- **Single responsibility:** One job per file. When a module grows, convert it to a folder with focused submodules.
- **Naming:** Prefer folder-first names (e.g., `parser/core.py` over `parser_core.py`). Keep module names clear and short.
- **Clarity first:** Write human-readable messages and docs. Avoid hidden magic or implied behaviors.

Single responsibility is enforced in CI. If CI fails with responsibility_check, split the file into a folder (e.g., executor/expr_eval.py, executor/statements.py). Keep files under 300 LOC when possible.

## Testing & Checks
- Add or update tests for every behavior. Use `python -m pytest -q` from the repo root.
- Compile check: `python -m compileall src -q` to catch syntax issues.
- Line limit: `python tools/line_limit_check.py` to verify the 500-line rule locally.
- CI runs all of the above on push/PR; keep runs fast and deterministic.

## Local checks
- `python -m compileall src -q`
- `python -m pytest -q`
- `python tools/line_limit_check.py`

## Workflow Expectations
- Keep PRs minimal and focused; avoid introducing features not requested.
- Document new surfaces in `README.md` or `docs/` as appropriate.
- Prefer explicit failures with actionable error messages over silent fallbacks.
