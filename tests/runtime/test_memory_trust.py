from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory_agreement.store import ProposalStore
from namel3ss.runtime.memory_trust import (
    approval_recorded_lines,
    can_approve,
    can_propose,
    trust_level_from_identity,
)
from namel3ss.runtime.memory_trust.model import TrustRules
from tests.conftest import lower_ir_program


def test_trust_level_mapping_from_identity():
    assert trust_level_from_identity({"trust_level": "approver"}) == "approver"
    assert trust_level_from_identity({"role": "owner"}) == "owner"
    assert trust_level_from_identity({"trust_level": "internal"}) == "approver"
    assert trust_level_from_identity({"role": "member"}) == "contributor"
    assert trust_level_from_identity({}) == "viewer"


def test_trust_decisions_default_rules():
    rules = TrustRules()
    assert can_propose("contributor", rules).allowed is True
    assert can_approve("contributor", rules).allowed is False
    assert can_approve("approver", rules).allowed is True


def test_trust_blocks_team_proposal_for_viewer():
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
    events = memory.record_interaction_with_events(
        ai,
        {},
        "Remember this for the project: We decided to ship weekly.",
        "ok",
        [],
        identity={"trust_level": "viewer", "id": "viewer-1"},
    )[1]
    assert any(event["type"] == "memory_trust_check" for event in events)
    assert not any(event["type"] == "memory_proposed" for event in events)


def test_two_approvals_required_behavior():
    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    item = factory.create(session="session:anon:my", kind=MemoryKind.SEMANTIC, text="alpha", source="user")
    store = ProposalStore()
    proposal = store.create_proposal(
        team_id="team-1",
        phase_id="phase-1",
        memory_item=item,
        proposed_by="user",
        reason_code="demo",
        approval_count_required=2,
        owner_override=False,
    )
    updated, recorded = store.record_approval(proposal.proposal_id, actor_id="alice")
    assert recorded is True
    assert updated is not None
    assert len(updated.approvals) == 1
    updated, recorded = store.record_approval(proposal.proposal_id, actor_id="alice")
    assert recorded is False
    assert updated is not None
    assert len(updated.approvals) == 1
    updated, recorded = store.record_approval(proposal.proposal_id, actor_id="bob")
    assert recorded is True
    assert updated is not None
    assert len(updated.approvals) == 2


def test_approval_lines_are_bracketless():
    lines = approval_recorded_lines(
        proposal_id="proposal-1",
        actor_id="user-1",
        count_now=1,
        count_required=2,
    )
    for line in lines:
        assert all(ch not in line for ch in "[]{}()")
