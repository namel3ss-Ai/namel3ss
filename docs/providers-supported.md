# Supported AI providers

- `openai` — set `NAMEL3SS_OPENAI_API_KEY` (optional `NAMEL3SS_OPENAI_BASE_URL`).
- `anthropic` — set `NAMEL3SS_ANTHROPIC_API_KEY`.
- `gemini` — set `NAMEL3SS_GEMINI_API_KEY`.
- `mistral` — set `NAMEL3SS_MISTRAL_API_KEY`.
- `ollama` — set `NAMEL3SS_OLLAMA_HOST` and optional `NAMEL3SS_OLLAMA_TIMEOUT_SECONDS`.
- `mock` — built-in mock provider for tests and offline development.

Run `n3 doctor` to verify provider env vars are detected before running flows.

Tool calling is supported for `mock`, `openai`, `anthropic`, `gemini`, and `mistral`; `ollama` is text-only.
