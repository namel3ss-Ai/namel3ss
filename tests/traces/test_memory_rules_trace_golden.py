import json
from pathlib import Path

from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory_agreement import AgreementRequest
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.runtime.memory_rules import RuleRequest
from tests.conftest import lower_ir_program


SOURCE = '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is true
'''


def test_memory_rules_trace_golden():
    program = lower_ir_program(SOURCE)
    ai = program.ais["assistant"]
    memory = MemoryManager()
    owner = {"trust_level": "owner", "id": "owner-1"}
    contributor = {"trust_level": "contributor", "id": "contributor-1"}
    state: dict = {}
    request = RuleRequest(
        text="Only approvers can approve team proposals",
        scope="team",
        priority=0,
        requested_by="owner-1",
    )
    memory.propose_rule_with_events(ai, state, request, identity=owner)
    team_id = resolve_team_id(project_root=None, app_path=None, config=None)
    proposal = memory.agreements.select_pending(team_id, None)
    assert proposal is not None
    approve_events = memory.apply_agreement_action(
        ai,
        state,
        AgreementRequest(action="approve", proposal_id=proposal.proposal_id, requested_by="owner-1"),
        identity=owner,
        team_id=team_id,
    )
    memory.record_interaction_with_events(
        ai,
        state,
        "Remember this for the project: We decided to ship weekly.",
        "ok",
        [],
        identity=contributor,
    )
    pending = memory.agreements.select_pending(team_id, None)
    assert pending is not None
    rule_events = memory.apply_agreement_action(
        ai,
        state,
        AgreementRequest(action="approve", proposal_id=pending.proposal_id, requested_by="contributor-1"),
        identity=contributor,
        team_id=team_id,
    )
    snapshot_state = {"_memory_rules_snapshot": "team"}
    _, snapshot_events = memory.record_interaction_with_events(
        ai,
        snapshot_state,
        "Show rule snapshot.",
        "ok",
        [],
        identity=owner,
    )
    trace_events: list[dict] = []
    for group in (approve_events, rule_events, snapshot_events):
        trace_events.extend(
            [
                event
                for event in group
                if event["type"]
                in {"memory_rule_applied", "memory_rules_snapshot", "memory_rule_changed"}
            ]
        )
    fixture_path = Path("tests/fixtures/memory_rules_trace_golden.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert trace_events == expected
