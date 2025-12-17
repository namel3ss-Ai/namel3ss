# Providers

## Supported providers and env vars

| Provider  | Env vars (required unless noted)                           | Notes                                  |
|-----------|------------------------------------------------------------|----------------------------------------|
| Ollama    | `NAMEL3SS_OLLAMA_HOST` (optional), `NAMEL3SS_OLLAMA_TIMEOUT_SECONDS` (optional) | Defaults: host `http://127.0.0.1:11434`, timeout 30s |
| OpenAI    | `NAMEL3SS_OPENAI_API_KEY`, `NAMEL3SS_OPENAI_BASE_URL` (optional, default `https://api.openai.com`) | Text output only                       |
| Anthropic | `NAMEL3SS_ANTHROPIC_API_KEY`                               | Text output only                       |
| Gemini    | `NAMEL3SS_GEMINI_API_KEY`                                  | Text output only                       |
| Mistral   | `NAMEL3SS_MISTRAL_API_KEY`                                 | Text output only                       |

Config is env-first; a config file under `~/.namel3ss/config.json` is optional. System prompts are supported; tool-calling is ignored for Tier-1 providers in this version, but the runtime still passes memory context and tool schemas for future support.

## Example (.ai)
```
ai "assistant":
  provider is "openai"
  model is "gpt-4.1"
  system_prompt is "You are helpful."

flow "demo":
  ask ai "assistant" with input: "Hello!" as reply
  return reply
```

Swap `provider`/`model` for:
- `ollama` + `llama3.1`
- `anthropic` + `claude-3-opus`
- `gemini` + `gemini-1.5-flash`
- `mistral` + `mistral-medium`

## Troubleshooting
- `Provider '<name>' requires <ENV_VAR>` → set the required env var.
- `Provider '<name>' authentication failed` → invalid/expired key or missing permissions.
- `Provider '<name>' unreachable` → network/DNS/firewall issues or local Ollama not running.
- `Provider '<name>' returned an invalid response` → wrong model name, upstream outage, or unexpected API response; retry or enable debug logging if available.
