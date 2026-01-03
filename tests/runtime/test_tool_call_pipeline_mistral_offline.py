from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE = '''tool "echo":
  implemented using builtin

  input:
    value is json

  output:
    echo is json

ai "assistant":
  provider is "mistral"
  model is "mistral-large-latest"
  tools:
    expose "echo"

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "ping" as reply
  return reply
'''


def test_mistral_pipeline_offline(monkeypatch):
    program = lower_ir_program(SOURCE)

    tool_call_response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"id": "call_1", "type": "function", "function": {"name": "echo", "arguments": {"value": "hi"}}}
                    ]
                }
            }
        ]
    }
    text_response = {"choices": [{"message": {"content": "[done]"}}]}
    responses = iter([tool_call_response, text_response])

    def fake_post_json(**kwargs):
        return next(responses)

    monkeypatch.setenv("NAMEL3SS_MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr("namel3ss.runtime.providers.mistral.tool_calls_adapter.post_json", fake_post_json)

    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_profiles=program.ais,
    )
    assert result.last_value == "[done]"
    trace = next(item for item in result.traces if hasattr(item, "canonical_events"))
    types = [event["type"] for event in trace.canonical_events]
    assert "tool_call_requested" in types
    assert "tool_call_completed" in types
    assert "ai_call_completed" in types
    call_ids = {event["call_id"] for event in trace.canonical_events if "call_id" in event}
    assert len(call_ids) == 1
