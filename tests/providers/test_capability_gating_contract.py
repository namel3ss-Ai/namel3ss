import pytest

from namel3ss.runtime.ai.provider import AIResponse
from namel3ss.runtime.providers.capabilities import _CAPABILITIES, ProviderCapabilities
from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE = '''tool "echo":
  kind is "builtin"

ai "assistant":
  provider is "{provider}"
  model is "test-model"
  tools:
    expose "echo"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''


class StubProvider:
    def ask(self, *, model, system_prompt, user_input, tools=None, memory=None, tool_results=None):
        return AIResponse(output=f"[{model}] ok")


def test_pipeline_not_used_when_capability_false(monkeypatch):
    provider_name = next(name for name, caps in _CAPABILITIES.items() if caps.supports_tools)
    program = lower_ir_program(SOURCE.format(provider=provider_name))

    def fake_capabilities(_name: str) -> ProviderCapabilities:
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
    monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider", lambda _name, _cfg: StubProvider())
    monkeypatch.setattr(
        "namel3ss.runtime.tool_calls.provider_iface.get_provider_adapter",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Adapter should not be used when tools disabled")),
    )

    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_profiles=program.ais,
    )
    trace = result.traces[0]
    types = [event["type"] for event in trace.canonical_events]
    assert "tool_call_requested" not in types
    assert types[-1] == "ai_call_completed"
