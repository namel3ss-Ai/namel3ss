from namel3ss.runtime.executor import execute_flow
from namel3ss.runtime.providers.capabilities import ProviderCapabilities
from tests.conftest import lower_ir_program


SOURCE = '''tool "echo":
  implemented using builtin

  input:
    value is json

  output:
    echo is json

ai "assistant":
  provider is "gemini"
  model is "gemini-1.5-flash"
  tools:
    expose "echo"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "ping" as reply
  return reply
'''


def test_gemini_pipeline_skipped_when_capability_off(monkeypatch):
    program = lower_ir_program(SOURCE)

    def fake_capabilities(name: str):
        return ProviderCapabilities(
            supports_tools=False,
            supports_json_mode=False,
            supports_streaming=False,
            supports_system_prompt=True,
            supports_vision=False,
            notes=None,
            max_context_tokens=None,
        )

    monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider_capabilities", fake_capabilities)
    monkeypatch.setenv("NAMEL3SS_GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("namel3ss.runtime.ai.providers.gemini.post_json", lambda **kwargs: {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_profiles=program.ais,
    )
    trace = result.traces[0]
    types = [event["type"] for event in trace.canonical_events]
    assert "tool_call_requested" not in types
    assert "ai_call_completed" in types
    assert "memory_write" in types
