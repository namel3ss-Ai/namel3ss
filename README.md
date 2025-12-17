# Namel3ss

Namel3ss is an English-first, AI-native programming language for building full-stack applications with deterministic behavior and inspectable AI.

```
pip install namel3ss
n3 new crud
n3 crud/app.ai studio
```

- [Quickstart](docs/quickstart.md)
- [Examples](examples/)
- [Changelog](CHANGELOG.md)

## Installation
- Requires Python 3.10+
- `pip install namel3ss`
- `n3 --help` to confirm the CLI entrypoint after installation.

## Run with Ollama (local)
- Ensure Ollama is running locally.
- In your `.ai`, set `provider is "ollama"` and a local model (e.g., `model is "llama3.1"`). If omitted, the provider defaults to `mock`.
- Optional env overrides: `NAMEL3SS_OLLAMA_HOST`, `NAMEL3SS_OLLAMA_TIMEOUT_SECONDS`.

## Run with Tier-1 providers (cloud)
- Env-first config (config file optional).
- OpenAI: export `NAMEL3SS_OPENAI_API_KEY` (optional `NAMEL3SS_OPENAI_BASE_URL`, defaults to `https://api.openai.com`).
- Anthropic (Claude): export `NAMEL3SS_ANTHROPIC_API_KEY`.
- Gemini: export `NAMEL3SS_GEMINI_API_KEY`.
- Mistral: export `NAMEL3SS_MISTRAL_API_KEY`.

### Provider selection example (.ai)
```
ai "assistant":
  provider is "openai"
  model is "gpt-4.1"
  system_prompt is "You are helpful."

flow "demo":
  ask ai "assistant" with input: "Hello!" as reply
  return reply
```
Swap `provider`/`model` to `anthropic`+`claude-3`, `gemini`+`gemini-1.5-flash`, `mistral`+`mistral-medium`, or `ollama`+`llama3.1`.

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

## Start a New App
- Scaffold: `n3 new <template> [project_name]` (templates: `crud`, `ai-assistant`, `multi-agent`)
- Names default to the template; hyphens become underscores on disk.
- After scaffolding: `cd <project>` then `n3 app.ai studio` or `n3 app.ai actions`.

## Repository Layout
- `src/namel3ss/`: language packages (lexer, parser, ast, ir, runtime, cli, errors, utils)
- `tests/`: pytest suite (add coverage for every feature)
- `docs/`: roadmap and language contracts
- `tools/`: repo-level utilities (line-limit enforcement)
- `.github/workflows/`: CI automation

## Architecture at a Glance
- Lexer → Parser → AST → IR → Runtime executor pipeline with deterministic defaults and explicit AI boundaries.
- CLI is file-first (`n3 app.ai ...`) with modes for run, check, lint, format, actions, and studio UI.
- Runtime supports providers via registry (mock, ollama, openai, anthropic, gemini, mistral) with env-first config and standardized errors.
- Memory manager handles short-term, semantic, and profile contexts passed into AI calls.
- Templates (`n3 new ...`) ship starter apps plus `.env`-safe `.gitignore` for secrets.

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
- [Providers](docs/providers.md)
- [Roadmap](docs/roadmap.md)

## Troubleshooting (providers)
- `Provider '<name>' requires <ENV_VAR>` → set the env var for that provider.
- `Provider '<name>' authentication failed` → check API key/permissions.
- `Provider '<name>' unreachable` → check network/DNS/firewall or ensure Ollama is running for local.
- `Provider '<name>' returned an invalid response` → verify model name, upstream status, and try again.
