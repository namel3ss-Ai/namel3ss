from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory_agreement import (
    AgreementCounts,
    AgreementRequest,
    agreement_summary,
    approved_lines,
    proposed_lines,
    rejected_lines,
)
from namel3ss.runtime.memory_agreement.store import ProposalStore
from namel3ss.runtime.memory_lanes.model import LANE_TEAM
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from tests.conftest import lower_ir_program


def test_proposal_store_ordering():
    clock = MemoryClock()
    factory = MemoryItemFactory(clock=clock, id_generator=MemoryIdGenerator())
    store = ProposalStore()
    item_a = factory.create(session="session:anon:my", kind=MemoryKind.SEMANTIC, text="alpha", source="user")
    item_b = factory.create(session="session:anon:my", kind=MemoryKind.SEMANTIC, text="beta", source="user")
    first = store.create_proposal(
        team_id="team-1",
        phase_id="phase-1",
        memory_item=item_a,
        proposed_by="user",
        reason_code="demo",
        ai_profile="assistant",
    )
    second = store.create_proposal(
        team_id="team-1",
        phase_id="phase-1",
        memory_item=item_b,
        proposed_by="user",
        reason_code="demo",
        ai_profile="assistant",
    )
    pending = store.list_pending("team-1")
    assert [entry.proposal_id for entry in pending] == [first.proposal_id, second.proposal_id]


def test_team_promotion_creates_proposal():
    program = lower_ir_program(
        '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is true
    profile is false
'''
    )
    ai = program.ais["assistant"]
    memory = MemoryManager()
    identity = {"trust_level": "contributor", "id": "user-1"}
    state: dict = {}
    written, events = memory.record_interaction_with_events(
        ai,
        state,
        "Remember this for the project: We decided to ship weekly.",
        "ok",
        [],
        identity=identity,
    )
    assert any(event["type"] == "memory_proposed" for event in events)
    assert not any(item for item in written if item.get("meta", {}).get("lane") == LANE_TEAM)
    team_id = resolve_team_id(project_root=None, app_path=None, config=None)
    assert memory.agreements.list_pending(team_id)


def test_approve_proposal_writes_team_memory():
    program = lower_ir_program(
        '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is true
    profile is false
'''
    )
    ai = program.ais["assistant"]
    memory = MemoryManager()
    identity = {"trust_level": "approver", "id": "approver-1"}
    state: dict = {}
    _written, _events = memory.record_interaction_with_events(
        ai,
        state,
        "Remember this for the project: We decided to ship weekly.",
        "ok",
        [],
        identity=identity,
    )
    team_id = resolve_team_id(project_root=None, app_path=None, config=None)
    proposal = memory.agreements.select_pending(team_id, None)
    assert proposal is not None
    events = memory.apply_agreement_action(
        ai,
        state,
        AgreementRequest(action="approve", proposal_id=proposal.proposal_id, requested_by="user"),
        identity=identity,
    )
    assert any(event["type"] == "memory_approved" for event in events)
    team_items = [item for item in memory.semantic.all_items() if item.meta.get("lane") == LANE_TEAM]
    assert any(item.meta.get("agreement_status") == "approved" for item in team_items)
    assert not memory.agreements.list_pending(team_id)


def test_reject_proposal_removes_pending():
    program = lower_ir_program(
        '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is true
    profile is false
'''
    )
    ai = program.ais["assistant"]
    memory = MemoryManager()
    identity = {"trust_level": "approver", "id": "approver-1"}
    state: dict = {}
    _written, _events = memory.record_interaction_with_events(
        ai,
        state,
        "Remember this for the project: We decided to ship weekly.",
        "ok",
        [],
        identity=identity,
    )
    team_id = resolve_team_id(project_root=None, app_path=None, config=None)
    proposal = memory.agreements.select_pending(team_id, None)
    assert proposal is not None
    events = memory.apply_agreement_action(
        ai,
        state,
        AgreementRequest(action="reject", proposal_id=proposal.proposal_id, requested_by="user"),
        identity=identity,
    )
    assert any(event["type"] == "memory_rejected" for event in events)
    assert not memory.agreements.list_pending(team_id)


def test_agreement_lines_are_bracketless():
    summary = agreement_summary(AgreementCounts(approved=1, rejected=2, pending=1))
    lines = summary.lines
    for line in lines:
        assert all(ch not in line for ch in "[]{}()")

    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    item = factory.create(session="session:anon:my", kind=MemoryKind.SEMANTIC, text="alpha", source="user")
    store = ProposalStore()
    proposal = store.create_proposal(
        team_id="team-1",
        phase_id="phase-1",
        memory_item=item,
        proposed_by="user",
        reason_code="demo",
        ai_profile="assistant",
    )
    for line in proposed_lines(proposal) + approved_lines(proposal, memory_id="id-1") + rejected_lines(proposal):
        assert all(ch not in line for ch in "[]{}()")
