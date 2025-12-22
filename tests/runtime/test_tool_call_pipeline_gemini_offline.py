from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE = '''tool "echo":
  kind is "builtin"

ai "assistant":
  provider is "gemini"
  model is "gemini-1.5-flash"
  tools:
    expose "echo"

flow "demo":
  ask ai "assistant" with input: "ping" as reply
  return reply
'''


def test_gemini_pipeline_offline(monkeypatch):
    program = lower_ir_program(SOURCE)

    tool_call_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {
                                "name": "echo",
                                "args": {"value": "hi"},
                            }
                        }
                    ]
                }
            }
        ]
    }
    text_response = {"candidates": [{"content": {"parts": [{"text": "[done]"}]}}]}
    responses = iter([tool_call_response, text_response])

    def fake_post_json(**kwargs):
        return next(responses)

    monkeypatch.setenv("NAMEL3SS_GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("namel3ss.runtime.providers.gemini.tool_calls_adapter.post_json", fake_post_json)

    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_profiles=program.ais,
    )
    assert result.last_value == "[done]"
    trace = result.traces[0]
    types = [event["type"] for event in trace.canonical_events]
    assert "tool_call_requested" in types
    assert "tool_call_completed" in types
    assert types[-1] == "ai_call_completed"
    call_ids = {event["call_id"] for event in trace.canonical_events}
    assert len(call_ids) == 1
