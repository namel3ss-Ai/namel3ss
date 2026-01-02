from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.studio.diagnostics import (
    collect_ai_context_diagnostics,
    collect_runtime_ai_context_diagnostics,
)


SOURCE_MISSING_CONTEXT = '''
spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

record "Order":
  id number

flow "ask_ai":
  find "Order" where true
  ask ai "assistant" with input: input.values.question as reply
  return reply

page "home":
  button "Ask":
    calls flow "ask_ai"
'''.lstrip()


SOURCE_WITH_CONTEXT = '''
spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

record "Order":
  id number

flow "ask_ai":
  find "Order" where true
  let prompt is order_results
  ask ai "assistant" with input: prompt as reply
  return reply
'''.lstrip()


SOURCE_NO_QUERY = '''
spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "creative":
  ask ai "assistant" with input: "Write a short poem." as reply
  return reply
'''.lstrip()


def _diagnostics_for(source: str) -> list[dict]:
    program = lower_program(parse(source))
    return collect_ai_context_diagnostics(program)


def test_ai_context_static_detection_positive():
    diagnostics = _diagnostics_for(SOURCE_MISSING_CONTEXT)
    assert any(item.get("id") == "AI_CONTEXT_MISSING" for item in diagnostics)
    assert any(item.get("flow") == "ask_ai" for item in diagnostics)


def test_ai_context_static_detection_negative():
    diagnostics = _diagnostics_for(SOURCE_WITH_CONTEXT)
    assert not any(item.get("id") == "AI_CONTEXT_MISSING" for item in diagnostics)


def test_ai_context_runtime_detection():
    traces = [
        {"type": "tool_call", "tool": "fetch", "status": "ok"},
        {"ai_name": "assistant", "input": "Which region has the lowest returns?"},
    ]
    diagnostics = collect_runtime_ai_context_diagnostics(traces)
    assert any(item.get("id") == "AI_CONTEXT_LIKELY_MISSING" for item in diagnostics)


def test_ai_context_runtime_detection_empty_context():
    traces = [
        {"type": "tool_call", "tool": "fetch", "status": "ok"},
        {
            "ai_name": "assistant",
            "input": "Orders: (none found)\n\nQuestion: Which region has the lowest returns?",
        },
    ]
    diagnostics = collect_runtime_ai_context_diagnostics(traces)
    assert not any(item.get("id") == "AI_CONTEXT_LIKELY_MISSING" for item in diagnostics)


def test_ai_context_no_query_guard():
    diagnostics = _diagnostics_for(SOURCE_NO_QUERY)
    assert not diagnostics
