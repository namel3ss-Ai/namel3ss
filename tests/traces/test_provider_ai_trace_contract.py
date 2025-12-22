from namel3ss.runtime.ai.provider import AIResponse
from namel3ss.runtime.ai.providers import registry as provider_registry
from namel3ss.runtime.providers.capabilities import get_provider_capabilities
from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE_TEMPLATE = '''ai "assistant":
  provider is "{provider}"
  model is "test-model"

flow "demo":
  ask ai "assistant" with input: "hi" as reply
  return reply
'''


class StubProvider:
    def ask(self, *, model, system_prompt, user_input, tools=None, memory=None, tool_results=None):
        return AIResponse(output=f"[{model}] ok")


def test_text_only_traces_for_all_providers(monkeypatch):
    provider_ids = set(provider_registry._FACTORIES.keys())
    for name in provider_ids:
        program = lower_ir_program(SOURCE_TEMPLATE.format(provider=name))
        monkeypatch.setattr("namel3ss.runtime.executor.ai_runner.get_provider", lambda _name, _cfg: StubProvider())
        result = execute_flow(
            program.flows[0],
            schemas={schema.name: schema for schema in program.records},
            initial_state={},
            ai_profiles=program.ais,
        )
        trace = result.traces[0]
        events = trace.canonical_events
        assert events[0]["type"] == "ai_call_started"
        assert events[-1]["type"] in {"ai_call_completed", "ai_call_failed"}
        for event in events:
            assert "trace_version" in event
            assert event["provider"] == name
            assert "call_id" in event
