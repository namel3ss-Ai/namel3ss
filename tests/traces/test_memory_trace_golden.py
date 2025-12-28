import json
from pathlib import Path

from namel3ss.runtime.ai.providers.mock import MockProvider
from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 2
    semantic is true

flow "demo":
  ask ai "assistant" with input: "Hello" as first
  ask ai "assistant" with input: "Hello" as second
'''


def test_memory_trace_golden():
    program = lower_ir_program(SOURCE)
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_provider=MockProvider(),
        ai_profiles=program.ais,
    )
    trace = result.traces[-1]
    memory_events = [event for event in trace.canonical_events if event["type"] in {"memory_recall", "memory_write"}]
    fixture_path = Path("tests/fixtures/memory_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert memory_events == expected
