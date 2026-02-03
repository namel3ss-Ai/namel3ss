from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.ai.provider import AIResponse
from tests.conftest import run_flow


def _capture_inputs(monkeypatch):
    captured: list[str] = []

    def fake_ask(self, *, model, system_prompt, user_input, tools=None, memory=None, tool_results=None):
        captured.append(user_input)
        return AIResponse(output="ok")

    monkeypatch.setattr(MockProvider, "ask", fake_ask)
    return captured


def test_ask_ai_structured_input_serializes_deterministically(monkeypatch):
    source = '''spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "demo":
  let payload is map:
    "question" is "Hello"
    "context" is list:
      "a",
      "b"
  ask ai "assistant" with structured input from payload as reply
  return reply
'''
    captured = _capture_inputs(monkeypatch)
    result = run_flow(source)
    expected = '{"context":["a","b"],"question":"Hello"}'
    assert captured == [expected]
    trace = result.traces[0]
    assert trace.input == expected
    assert trace.input_structured == {"question": "Hello", "context": ["a", "b"]}
    assert trace.input_format == "structured_json_v1"


def test_structured_input_preserves_list_order(monkeypatch):
    source = '''spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "demo":
  let payload is list:
    map:
      "score" is 2
      "id" is "b"
    map:
      "score" is 1
      "id" is "a"
  ask ai "assistant" with structured input from payload as reply
  return reply
'''
    captured = _capture_inputs(monkeypatch)
    run_flow(source)
    expected = '[{"id":"b","score":2},{"id":"a","score":1}]'
    assert captured == [expected]


def test_structured_input_replayable_and_empty_values(monkeypatch):
    source = '''spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "demo":
  let payload is map:
    "items" is list:
    "meta" is map:
  ask ai "assistant" with structured input from payload as reply
  return reply
'''
    captured = _capture_inputs(monkeypatch)
    run_flow(source)
    run_flow(source)
    expected = '{"items":[],"meta":{}}'
    assert captured == [expected, expected]


def test_run_agent_structured_input(monkeypatch):
    source = '''spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

agent "planner":
  ai is "assistant"

flow "demo":
  let payload is map:
    "topic" is "Launch"
    "steps" is list:
      "prep",
      "ship"
  run agent "planner" with structured input from payload as reply
  return reply
'''
    captured = _capture_inputs(monkeypatch)
    run_flow(source)
    expected = '{"steps":["prep","ship"],"topic":"Launch"}'
    assert captured == [expected]
