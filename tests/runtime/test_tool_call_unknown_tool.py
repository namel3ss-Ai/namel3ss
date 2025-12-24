import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIToolCallResponse
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

flow "demo":
  ask ai "assistant" with input: "ping" as reply
  return reply
'''


def test_unknown_tool_from_model_is_error():
    program = lower_ir_program(SOURCE)
    provider = MockProvider(tool_call_sequence=[AIToolCallResponse(tool_name="unknown_tool", args={"x": 1})])
    with pytest.raises(Namel3ssError) as exc:
        execute_flow(
            program.flows[0],
            schemas={schema.name: schema for schema in program.records},
            initial_state={},
            ai_provider=provider,
            ai_profiles=program.ais,
        )
    assert "unknown tool" in str(exc.value)
