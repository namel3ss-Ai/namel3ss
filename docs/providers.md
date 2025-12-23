# Provider capabilities (Phase 10A)

This registry documents what each AI provider supports so Studio and the engine can make consistent choices. It is read-only in this phase; tool calling is not implemented for real providers yet.

## Implemented now
| Provider | Tools | JSON mode | Streaming | System prompt | Vision | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| mock | Yes | No | No | Yes | No | Test double that can emit tool calls via a seeded sequence. |
| ollama | No | No | No | Yes | No | Text chat endpoint only; no tool calling or JSON mode wiring yet. |
| openai | No | No | No | Yes | No | Uses `/v1/responses` with text output; tool calling not wired. |
| anthropic | No | No | No | Yes | No | Text-only messages API; tool calling not wired. |
| gemini | No | No | No | Yes | No | System prompt is appended to the user message; text-only path. |
| mistral | No | No | No | Yes | No | Chat completions path without tool calling or JSON mode. |

## Planned / not implemented yet
- Tool calling for real providers
- Structured / JSON mode responses
- Streaming responses
- Vision inputs or outputs
