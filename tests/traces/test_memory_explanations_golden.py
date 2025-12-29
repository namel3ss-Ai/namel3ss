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
    profile is true

spec is "1.0"

flow "demo":
  ask ai "assistant" with input: "My name is Ada." as first
  ask ai "assistant" with input: "Actually, my name is Ada Lovelace." as second
  set state._memory_phase_token is "phase-2"
  ask ai "assistant" with input: "my password is 123" as third
  set state._memory_phase_diff_from is "phase-1"
  set state._memory_phase_diff_to is "phase-2"
  ask ai "assistant" with input: "Show diff." as fourth
'''


def test_memory_explanations_golden():
    program = lower_ir_program(SOURCE)
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_provider=MockProvider(),
        ai_profiles=program.ais,
    )
    explanation_events = []
    for trace in result.traces:
        explanation_events.extend(
            [event for event in trace.canonical_events if event["type"] == "memory_explanation"]
        )
    fixture_path = Path("tests/fixtures/memory_explanations_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert explanation_events == expected
