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
  set state._memory_trust_action is "change_rules"
  set state._memory_trust_approval_count is 2
  set state._memory_trust_owner_override is "false"
  ask ai "assistant" with input: "Set trust rules." as rules
  ask ai "assistant" with input: "Remember this for the project: We decided to ship weekly." as first
  set state._memory_agreement_action is "approve"
  set state._memory_agreement_by is "approver-one"
  ask ai "assistant" with input: "Approve once." as approve_one
  set state._memory_agreement_by is "approver-two"
  ask ai "assistant" with input: "Approve twice." as approve_two
  set state._memory_agreement_action is ""
  set state._memory_trust_action is ""
'''


def test_memory_trust_trace_golden():
    program = lower_ir_program(SOURCE)
    result = execute_flow(
        program.flows[0],
        schemas={schema.name: schema for schema in program.records},
        initial_state={},
        ai_provider=MockProvider(),
        ai_profiles=program.ais,
        identity={"trust_level": "owner"},
    )
    events = []
    for trace in result.traces:
        events.extend(
            [
                event
                for event in trace.canonical_events
                if event["type"]
                in {
                    "memory_trust_check",
                    "memory_approval_recorded",
                    "memory_trust_rules",
                }
            ]
        )
    fixture_path = Path("tests/fixtures/memory_trust_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert events == expected
