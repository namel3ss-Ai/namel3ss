import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory_agreement import AgreementRequest
from namel3ss.runtime.memory.events import EVENT_PREFERENCE
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.runtime.memory_rules import (
    ACTION_APPROVE_TEAM_MEMORY,
    ACTION_HANDOFF_APPLY,
    ACTION_HANDOFF_CREATE,
    ACTION_HANDOFF_REJECT,
    ACTION_PROPOSE_TEAM_MEMORY,
    RULE_SCOPE_TEAM,
    RULE_STATUS_ACTIVE,
    Rule,
    RuleRequest,
    active_rules_for_store,
    evaluate_rules,
    parse_rule_text,
    rule_lane_for_scope,
    rule_space_for_scope,
    rule_applied_lines,
    rule_changed_lines,
    rules_snapshot_lines,
)
from tests.conftest import lower_ir_program


def _rule(text: str, *, rule_id: str = "rule-1") -> Rule:
    return Rule(
        rule_id=rule_id,
        text=text,
        scope=RULE_SCOPE_TEAM,
        lane="team",
        phase_id="phase-1",
        status=RULE_STATUS_ACTIVE,
        created_by="tester",
        created_at=1,
        priority=0,
    )


def test_rule_parsing_valid_sentences():
    spec = parse_rule_text("Only approvers can approve team proposals")
    assert spec.kind == "min_level"
    assert spec.level == "approver"
    assert ACTION_APPROVE_TEAM_MEMORY in spec.actions
    create_spec = parse_rule_text("Only contributors can create handoff packets")
    assert create_spec.kind == "min_level"
    assert ACTION_HANDOFF_CREATE in create_spec.actions
    apply_spec = parse_rule_text("Only approvers can apply handoff packets")
    assert apply_spec.kind == "min_level"
    assert ACTION_HANDOFF_APPLY in apply_spec.actions
    reject_spec = parse_rule_text("Only owners can reject handoff packets")
    assert reject_spec.kind == "min_level"
    assert ACTION_HANDOFF_REJECT in reject_spec.actions
    count_spec = parse_rule_text("Two approvals are needed for team changes")
    assert count_spec.kind == "approval_count"
    assert count_spec.count == 2
    deny_spec = parse_rule_text("Team memory cannot store personal preferences")
    assert deny_spec.kind == "deny_event"
    assert deny_spec.event_type == EVENT_PREFERENCE


def test_rule_parsing_rejects_unknown_sentence():
    with pytest.raises(Namel3ssError):
        parse_rule_text("Allow anyone to do anything")


def test_rule_evaluation_blocks_low_trust():
    rule = _rule("Only approvers can approve team proposals")
    check = evaluate_rules(rules=[rule], action=ACTION_APPROVE_TEAM_MEMORY, actor_level="contributor")
    assert check.allowed is False
    assert check.applied[0].allowed is False


def test_rule_evaluation_requires_two_approvals():
    rule = _rule("Two approvals are needed for team changes", rule_id="rule-2")
    check = evaluate_rules(rules=[rule], action=ACTION_APPROVE_TEAM_MEMORY, actor_level="owner")
    assert check.allowed is True
    assert check.required_approvals == 2


def test_rule_evaluation_denies_preference_event():
    rule = _rule("Team memory cannot store personal preferences", rule_id="rule-3")
    check = evaluate_rules(
        rules=[rule],
        action=ACTION_PROPOSE_TEAM_MEMORY,
        actor_level="owner",
        event_type=EVENT_PREFERENCE,
    )
    assert check.allowed is False


def test_rule_evaluation_blocks_handoff_apply_for_low_trust():
    rule = _rule("Only approvers can apply handoff packets", rule_id="rule-4")
    check = evaluate_rules(rules=[rule], action=ACTION_HANDOFF_APPLY, actor_level="contributor")
    assert check.allowed is False


def test_rule_lines_are_bracketless():
    rule = _rule("Only approvers can approve team proposals")
    applied = evaluate_rules(rules=[rule], action=ACTION_APPROVE_TEAM_MEMORY, actor_level="owner").applied[0]
    lines = rule_applied_lines(applied) + rules_snapshot_lines([rule]) + rule_changed_lines([rule], [])
    for line in lines:
        assert all(ch not in line for ch in "[]{}()")


def test_rule_replacement_deletes_old_rule():
    program = lower_ir_program(
        '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is true
'''
    )
    ai = program.ais["assistant"]
    memory = MemoryManager()
    identity = {"trust_level": "owner", "id": "owner-1"}
    state: dict = {}
    request = RuleRequest(
        text="Team memory cannot store personal preferences",
        scope="team",
        priority=0,
        requested_by="owner-1",
    )
    memory.propose_rule_with_events(ai, state, request, identity=identity)
    team_id = resolve_team_id(project_root=None, app_path=None, config=None)
    proposal = memory.agreements.select_pending(team_id, None)
    assert proposal is not None
    memory.apply_agreement_action(
        ai,
        state,
        AgreementRequest(action="approve", proposal_id=proposal.proposal_id, requested_by="owner-1"),
        identity=identity,
        team_id=team_id,
    )
    memory.propose_rule_with_events(ai, state, request, identity=identity)
    proposal = memory.agreements.select_pending(team_id, None)
    assert proposal is not None
    events = memory.apply_agreement_action(
        ai,
        state,
        AgreementRequest(action="approve", proposal_id=proposal.proposal_id, requested_by="owner-1"),
        identity=identity,
        team_id=team_id,
    )
    space_ctx = memory.space_context(state, identity=identity)
    store_key = space_ctx.store_key_for(
        rule_space_for_scope("team"),
        lane=rule_lane_for_scope("team"),
    )
    active = active_rules_for_store(memory.semantic.items_for_store(store_key))
    assert len(active) == 1
    deleted_events = [event for event in events if event["type"] == "memory_deleted" and event["reason"] == "replaced"]
    assert deleted_events
    assert deleted_events[0]["replaced_by"] == active[0].rule_id
