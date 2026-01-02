from namel3ss.runtime.ai.provider import AIResponse
from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  provider is "mock"
  model is "test-model"
  memory:
    short_term is 1

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "ping" as reply
  return reply
'''


class StubProvider:
    def ask(self, *, model, system_prompt, user_input, tools=None, memory=None, tool_results=None):
        return AIResponse(output="ok")


def test_ai_output_stable_with_memory_traces():
    program = lower_ir_program(SOURCE)
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_provider=StubProvider(),
        ai_profiles=program.ais,
    )
    assert result.last_value == "ok"
    trace = result.traces[0]
    types = [event["type"] for event in trace.canonical_events]
    assert "memory_recall" in types
    assert "memory_write" in types
