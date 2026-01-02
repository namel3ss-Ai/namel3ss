from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIResponse, AIToolCallResponse
from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE = '''tool "echo":
  implemented using builtin

  input:
    value is json

  output:
    echo is json

ai "assistant":
  provider is "mock"
  model is "gpt-4.1"
  tools:
    expose "echo"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "ping" as reply
  return reply
'''


def test_pipeline_executes_tool_and_returns_output():
    program = lower_ir_program(SOURCE)
    provider = MockProvider(
        tool_call_sequence=[
            AIToolCallResponse(tool_name="echo", args={"value": "hi"}),
            AIResponse(output="[done]"),
        ]
    )
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_provider=provider,
        ai_profiles=program.ais,
    )
    assert result.last_value == "[done]"
    trace = result.traces[0]
    event_types = [event["type"] for event in trace.canonical_events]
    assert "tool_call_requested" in event_types
    assert "tool_call_completed" in event_types


def test_pipeline_wraps_scalar_tool_results(monkeypatch):
    program = lower_ir_program(SOURCE)
    provider = MockProvider(
        tool_call_sequence=[
            AIToolCallResponse(tool_name="echo", args={"value": "hi"}),
            AIResponse(output="[done]"),
        ]
    )
    monkeypatch.setattr("namel3ss.runtime.tools.executor.execute_builtin_tool", lambda name, args: "pong")
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_provider=provider,
        ai_profiles=program.ais,
    )
    trace = result.traces[0]
    tool_results = trace.tool_results
    assert tool_results
    assert isinstance(tool_results[0]["result"], dict)
    assert tool_results[0]["result"]["result"] == "pong"
