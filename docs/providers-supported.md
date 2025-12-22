# namel3ss Provider Support Report

## 1) Summary
- Providers discovered (registry + resolvers): 6 (`mock`, `ollama`, `openai`, `anthropic`, `gemini`, `mistral`).
- Production-ready today: mock (deterministic/dev), openai (text + normalized tool calls via adapter).
- Partially supported (text-only, no tools): ollama, anthropic, gemini, mistral.
- Mentioned and implemented consistently; no orphaned IDs outside the registry.

## 2) Supported Provider Matrix
| Provider ID | Text chat | Tool calling | JSON mode | Streaming | Notes |
| --- | --- | --- | --- | --- | --- |
| mock | Yes | Yes | No | No | Test/deterministic provider; tool calls via seeded sequence and pipeline. |
| openai | Yes | Yes | No | No | Chat completions with single tool call handled; requires `NAMEL3SS_OPENAI_API_KEY`. |
| ollama | Yes | No | No | No | Local `/api/chat` text path only; no tool wiring. |
| anthropic | Yes | Yes | No | No | Messages API with single tool call per turn; needs `NAMEL3SS_ANTHROPIC_API_KEY`. |
| gemini | Yes | Yes | No | No | Text path with single tool call per turn; needs `NAMEL3SS_GEMINI_API_KEY`. |
| mistral | Yes | Yes | No | No | Chat completions with single tool call per turn; needs `NAMEL3SS_MISTRAL_API_KEY`. |

Capabilities source: `src/namel3ss/runtime/providers/capabilities.py`.

## 3) Evidence (per provider)
- **Registry/resolution**: Factory IDs in `src/namel3ss/runtime/ai/providers/registry.py` and validation in `src/namel3ss/ir/lowering/ai.py` gate supported names.
- **mock**
  - Implementation: `src/namel3ss/runtime/ai/providers/mock.py`; always available via registry factory.
  - Tool pipeline: normalized adapter in `src/namel3ss/runtime/tool_calls/provider_iface.py` (MockProviderAdapter).
  - Env vars: none.
  - Tests: tool pipeline (`tests/runtime/test_tool_call_pipeline_mock.py`), traces (`tests/runtime/test_traces_tool_events.py`), capability matrix.
- **openai**
  - Implementation: text client `src/namel3ss/runtime/ai/providers/openai.py`; tool adapter `src/namel3ss/runtime/providers/openai/tool_calls_adapter.py`.
  - Resolution: registry factory uses `OpenAIProvider.from_config`; tool pipeline picks adapter via `get_provider_adapter`.
  - Env vars: `NAMEL3SS_OPENAI_API_KEY` (require_env); base URL from config.
  - Tests: adapter parsing (`tests/providers/test_openai_tool_calls_adapter_parsing.py`), offline pipeline (`tests/runtime/test_tool_call_pipeline_openai_offline.py`), selection (`tests/integration/test_ai_provider_selection_tier1.py`), provider contracts (`tests/runtime/test_openai_provider.py`), capability registry (`tests/providers/test_capabilities.py`).
- **ollama**
  - Implementation: `src/namel3ss/runtime/ai/providers/ollama.py`; host/timeout from config.
  - Tool pipeline: not wired; capabilities disable tools.
  - Env vars: none (config-driven).
  - Tests: provider contracts (`tests/runtime/test_ollama_provider.py`, `tests/runtime/test_provider_contract_matrix.py`), capability registry.
- **anthropic**
  - Implementation: `src/namel3ss/runtime/ai/providers/anthropic.py`; uses messages API.
  - Tool pipeline: not wired; capabilities disable tools.
  - Env vars: `NAMEL3SS_ANTHROPIC_API_KEY`.
  - Tests: `tests/runtime/test_anthropic_provider.py`, contract matrix, capability registry.
- **gemini**
  - Implementation: `src/namel3ss/runtime/ai/providers/gemini.py`; text-only content.
  - Tool pipeline: not wired; capabilities disable tools.
  - Env vars: `NAMEL3SS_GEMINI_API_KEY`.
  - Tests: `tests/runtime/test_gemini_provider.py`, contract matrix, capability registry.
- **mistral**
  - Implementation: `src/namel3ss/runtime/ai/providers/mistral.py`; chat completions text-only.
  - Tool pipeline: not wired; capabilities disable tools.
  - Env vars: `NAMEL3SS_MISTRAL_API_KEY`.
  - Tests: `tests/runtime/test_mistral_provider.py`, contract matrix, capability registry.

## 4) Gaps / Mismatches
- Tool calling is end-to-end only for `openai` (and `mock` for testing); other real providers are text-only despite capability hints (marked as no tools).
- No providers are listed in docs without code; registry and implementation lists match.
- Streaming/JSON mode unsupported across all providers; capabilities reflect this.

## 5) Recommendations (no code)
1) Add tool-calling adapters for next providers (e.g., Anthropics) using the normalized pipeline; mirror the OpenAI adapter pattern.
2) Expand capability docs to note tool-calling scope per provider and link to adapter tests.
3) Add streaming/JSON-mode capability enforcement tests once any provider supports them.
4) Keep capability registry and provider factories in lockstep; add a CI check that every registry entry has a resolver and vice versa.

No behavior changes were made.
