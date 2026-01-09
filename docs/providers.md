# Provider capabilities

This registry documents what each AI provider supports so Studio and the engine can make consistent choices. It is read-only in this phase; capabilities are enforced by the runtime and traces.

## Implemented now
| Provider | Tools | JSON mode | Streaming | System prompt | Vision | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| mock | Yes | No | No | Yes | No | Deterministic test double that can emit tool calls via a seeded sequence. |
| ollama | No | No | No | Yes | No | Text chat endpoint only; no tool calling. |
| openai | Yes | No | No | Yes | No | Tool calling via chat completions; canonical tool-call lifecycle traces. |
| anthropic | Yes | No | No | Yes | No | Tool calling via messages; canonical tool-call lifecycle traces. |
| gemini | Yes | No | No | Yes | No | Tool calling via tool adapter; system prompt is appended to the user message. |
| mistral | Yes | No | No | Yes | No | Tool calling via chat adapter; canonical tool-call lifecycle traces. |

## Planned / not implemented yet
- Structured / JSON mode responses
- Streaming responses
- Vision inputs or outputs
- Multiple tool calls in a single provider response
