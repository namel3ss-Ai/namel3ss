import itertools

import pytest

from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE = '''tool "echo":
  implemented using builtin

  input:
    value is json

  output:
    echo is json

ai "assistant":
  provider is "openai"
  model is "gpt-4.1"
  tools:
    expose "echo"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "ping" as reply
  return reply
'''


def test_openai_pipeline_offline_tool_call(monkeypatch):
    program = lower_ir_program(SOURCE)

    tool_call_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {"id": "call_1", "type": "function", "function": {"name": "echo", "arguments": '{"value":"hi"}'}}
                    ],
                }
            }
        ]
    }
    text_response = {"choices": [{"message": {"content": "[done]"}}]}
    responses = iter([tool_call_response, text_response])

    def fake_post_json(**kwargs):
        return next(responses)

    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("namel3ss.runtime.providers.openai.tool_calls_adapter.post_json", fake_post_json)

    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_profiles=program.ais,
    )
    assert result.last_value["text"] == "[done]"
    trace = result.traces[0]
    event_types = [event["type"] for event in trace.canonical_events]
    assert "tool_call_requested" in event_types
    assert "tool_call_completed" in event_types
    assert "ai_call_completed" in event_types
    call_ids = {event["call_id"] for event in trace.canonical_events if "call_id" in event}
    assert len(call_ids) == 1
