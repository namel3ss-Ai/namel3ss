import json
from pathlib import Path

from namel3ss.runtime.ai.providers.mock import MockProvider
from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 0
    semantic is true
    profile is true

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "Remember this for me: I prefer concise updates." as first
  ask ai "assistant" with input: "My name is Ada." as second
  ask ai "assistant" with input: "Actually, my name is Ada Lovelace." as third
'''


def test_memory_links_trace_golden():
    program = lower_ir_program(SOURCE)
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_provider=MockProvider(),
        ai_profiles=program.ais,
    )
    link_events = []
    for trace in result.traces:
        link_events.extend(
            [event for event in trace.canonical_events if event["type"] in {"memory_links", "memory_path"}]
        )
    fixture_path = Path("tests/fixtures/memory_links_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert link_events == expected
