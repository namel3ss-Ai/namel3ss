import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIToolCallResponse
from namel3ss.runtime.executor import Executor, execute_flow
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


def test_tool_call_max_limit_enforced():
    program = lower_ir_program(SOURCE)
    provider = MockProvider(
        tool_call_sequence=[
            AIToolCallResponse(tool_name="echo", args={"n": 1}),
            AIToolCallResponse(tool_name="echo", args={"n": 2}),
            AIToolCallResponse(tool_name="echo", args={"n": 3}),
            AIToolCallResponse(tool_name="echo", args={"n": 4}),
        ]
    )
    with pytest.raises(Namel3ssError) as exc:
        execute_flow(
            program.flows[0],
            schemas={schema.name: schema for schema in program.records},
            initial_state={},
            ai_provider=provider,
            ai_profiles=program.ais,
        )
    assert "maximum tool calls" in str(exc.value)


def test_tool_call_limit_emits_loop_finished():
    program = lower_ir_program(SOURCE)
    provider = MockProvider(
        tool_call_sequence=[
            AIToolCallResponse(tool_name="echo", args={"n": 1}),
            AIToolCallResponse(tool_name="echo", args={"n": 2}),
            AIToolCallResponse(tool_name="echo", args={"n": 3}),
            AIToolCallResponse(tool_name="echo", args={"n": 4}),
        ]
    )
    executor = Executor(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        ai_profiles=program.ais,
        ai_provider=provider,
        tools=program.tools,
    )
    with pytest.raises(Namel3ssError):
        executor.run()
    trace = executor.traces[0]
    loop = next(event for event in trace.canonical_events if event.get("type") == "tool_loop_finished")
    assert loop["stop_reason"] == "max_calls"
