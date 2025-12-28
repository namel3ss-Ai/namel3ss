import json
from pathlib import Path

from namel3ss.runtime.ai.providers.mock import MockProvider
from namel3ss.runtime.executor import execute_flow
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is true
    profile is false

flow "demo":
  ask ai "assistant" with input: "Remember this for the project: We decided to ship weekly." as first
  set state._memory_phase_token is "phase-2"
  ask ai "assistant" with input: "Remember this for the project: We decided to ship every Monday." as second
  set state._memory_phase_diff_from is "phase-1"
  set state._memory_phase_diff_to is "phase-2"
  set state._memory_phase_diff_space is "project"
  set state._memory_phase_diff_lane is "team"
  ask ai "assistant" with input: "Show me the team change." as diff
'''


def test_memory_team_summary_trace_golden():
    program = lower_ir_program(SOURCE)
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_provider=MockProvider(),
        ai_profiles=program.ais,
        identity={"trust_level": "contributor", "id": "user-1"},
    )
    events = []
    for trace in result.traces:
        events.extend([event for event in trace.canonical_events if event["type"] == "memory_team_summary"])
    fixture_path = Path("tests/fixtures/memory_team_summary_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert events == expected
