from namel3ss.runtime.ai.provider import AIResponse, AIToolCallResponse
from namel3ss.runtime.providers.capabilities import _CAPABILITIES, ProviderCapabilities
from namel3ss.runtime.tool_calls.provider_iface import AssistantText, AssistantToolCall
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


class FakeAdapter:
    def __init__(self):
        self.calls = 0

    def run_model(self, messages, tools, policy):
        # First call: request a tool
        if self.calls == 0:
            self.calls += 1
            return AssistantToolCall(tool_call_id="tool-1", tool_name="echo", arguments_json_text='{"value":"hi"}')
        # Second call: return final text
        return AssistantText(text="[done]")


def test_tool_trace_contract(monkeypatch):
    providers = [name for name, caps in _CAPABILITIES.items() if caps.supports_tools]
    for name in providers:
        program = lower_ir_program(SOURCE.format(provider=name))
        # Force capabilities on to ensure pipeline is used
        monkeypatch.setattr(
            "namel3ss.runtime.executor.ai_runner.get_provider_capabilities",
            lambda _name, caps=_CAPABILITIES[name]: caps,
        )
        monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider", lambda _name, _cfg: object())
        monkeypatch.setattr(
            "namel3ss.runtime.tool_calls.provider_iface.get_provider_adapter",
            lambda provider_name, provider, model, system_prompt, adapter=FakeAdapter(): adapter,
        )
        result = execute_flow(
            program.flows[0],
            schemas={schema.name: schema for schema in program.records},
            initial_state={},
            ai_profiles=program.ais,
        )
        trace = result.traces[0]
        events = trace.canonical_events
        types = [event["type"] for event in events]
        assert "tool_call_requested" in types
        assert "tool_call_completed" in types
        assert types[-1] == "ai_call_completed"
        call_ids = {event["call_id"] for event in events}
        assert len(call_ids) == 1
        tool_ids = {event.get("tool_call_id") for event in events if "tool_call_id" in event}
        assert len(tool_ids) == 1
