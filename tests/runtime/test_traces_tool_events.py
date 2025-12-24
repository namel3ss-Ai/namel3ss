from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIResponse, AIToolCallResponse
from namel3ss.runtime.executor import execute_flow
from namel3ss.traces.schema import TraceEventType
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

flow "demo":
  ask ai "assistant" with input: "ping" as reply
  return reply
'''


def test_tool_trace_events_include_ids_and_order():
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
    trace = result.traces[0]
    events = trace.canonical_events
    types = [event["type"] for event in events]
    assert TraceEventType.TOOL_CALL_REQUESTED in types
    assert TraceEventType.TOOL_CALL_COMPLETED in types
    # Ensure call_id is reused across tool events
    call_ids = {event["call_id"] for event in events}
    assert len(call_ids) == 1
    tool_ids = {event.get("tool_call_id") for event in events if "tool_call_id" in event}
    assert len(tool_ids) == 1
    # Preserve order: request comes before completion
    assert types.index(TraceEventType.TOOL_CALL_REQUESTED) < types.index(TraceEventType.TOOL_CALL_COMPLETED)
