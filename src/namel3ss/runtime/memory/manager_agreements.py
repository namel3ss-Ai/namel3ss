from __future__ import annotations

from typing import Dict

from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.events import EVENT_RULE
from namel3ss.runtime.memory_agreement import AgreementRequest, build_proposed_event
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.runtime.memory_rules import (
    ACTION_APPROVE_TEAM_MEMORY,
    ACTION_PROPOSE_TEAM_MEMORY,
    RULE_STATUS_PENDING,
    RuleRequest,
    active_rules_for_scope,
    build_rule_item,
    enforce_action,
    merge_required_approvals,
    rule_lane_for_scope,
    rule_space_for_scope,
)
from namel3ss.runtime.memory_rules.traces import build_rule_applied_event
from namel3ss.runtime.memory_timeline.phase import phase_request_from_state
from namel3ss.runtime.memory_trust import (
    actor_id_from_identity,
    build_trust_check_event,
    build_trust_rules_event,
    can_change_rules,
    can_propose,
    required_approvals,
    rules_from_contract,
    rules_from_state,
    trust_level_from_identity,
)
from namel3ss.runtime.memory_trust.model import TRUST_OWNER
from namel3ss.runtime.memory.write_engine import apply_agreement_action as apply_agreement_action_engine
from namel3ss.runtime.memory.write_engine.phases import _ensure_phase_for_store


def propose_rule_with_events(
    manager,
    ai: ir.AIDecl,
    state: Dict[str, object],
    request: RuleRequest,
    *,
    identity: Dict[str, object] | None = None,
    project_root: str | None = None,
    app_path: str | None = None,
    team_id: str | None = None,
    agreement_defaults: dict | None = None,
) -> list[dict]:
    space_ctx = manager.space_context(
        state,
        identity=identity,
        project_root=project_root,
        app_path=app_path,
    )
    policy = manager.policy_for(ai)
    contract = manager.policy_contract_for(policy)
    phase_request = phase_request_from_state(state)
    resolved_team_id = team_id or resolve_team_id(project_root=project_root, app_path=app_path, config=None)
    events: list[dict] = []
    trust_rules = rules_from_contract(contract)
    actor_level = trust_level_from_identity(identity)
    actor_id = actor_id_from_identity(identity)
    if actor_id == "anonymous" and request.requested_by:
        actor_id = str(request.requested_by)
    override_rules = rules_from_state(state, trust_rules)
    if override_rules is not None:
        decision = can_change_rules(actor_level, trust_rules)
        events.append(
            build_trust_check_event(
                ai_profile=ai.name,
                session=space_ctx.session_id,
                action="change_rules",
                actor_id=actor_id,
                actor_level=decision.actor_level,
                required_level=decision.required_level,
                allowed=decision.allowed,
                reason=decision.reason,
            )
        )
        if decision.allowed:
            trust_rules = override_rules
    events.append(
        build_trust_rules_event(
            ai_profile=ai.name,
            session=space_ctx.session_id,
            team_id=resolved_team_id,
            rules=trust_rules,
        )
    )
    team_rules = active_rules_for_scope(semantic=manager.semantic, space_ctx=space_ctx, scope="team")
    rule_check = enforce_action(
        rules=team_rules,
        action=ACTION_PROPOSE_TEAM_MEMORY,
        actor_level=actor_level,
        event_type=EVENT_RULE,
    )
    if rule_check.applied:
        for applied in rule_check.applied:
            events.append(
                build_rule_applied_event(
                    ai_profile=ai.name,
                    session=space_ctx.session_id,
                    applied=applied,
                )
            )
    if not rule_check.allowed:
        return events
    propose_decision = can_propose(actor_level, trust_rules)
    events.append(
        build_trust_check_event(
            ai_profile=ai.name,
            session=space_ctx.session_id,
            action="propose",
            actor_id=actor_id,
            actor_level=propose_decision.actor_level,
            required_level=propose_decision.required_level,
            allowed=propose_decision.allowed,
            reason=propose_decision.reason,
        )
    )
    if not propose_decision.allowed:
        return events
    scope = request.scope
    lane = rule_lane_for_scope(scope)
    space = rule_space_for_scope(scope)
    owner = space_ctx.owner_for(space)
    store_key = space_ctx.store_key_for(space, lane=lane)
    phase, phase_events = _ensure_phase_for_store(
        ai_profile=ai.name,
        session=space_ctx.session_id,
        space=space,
        owner=owner,
        store_key=store_key,
        contract=contract,
        phase_registry=manager._phases,
        phase_ledger=manager._ledger,
        request=phase_request,
        default_reason="agreement",
        lane=lane,
    )
    events.extend(phase_events)
    rule_item, _ = build_rule_item(
        factory=manager._factory,
        store_key=store_key,
        text=request.text,
        source="user",
        scope=scope,
        lane=lane,
        space=space,
        owner=owner,
        phase=phase,
        status=RULE_STATUS_PENDING,
        priority=request.priority,
        created_by=request.requested_by,
    )
    approval_rules = enforce_action(
        rules=team_rules,
        action=ACTION_APPROVE_TEAM_MEMORY,
        actor_level=TRUST_OWNER,
        event_type=EVENT_RULE,
    )
    approvals_required = merge_required_approvals(
        _agreement_approval_count(trust_rules, agreement_defaults),
        approval_rules.required_approvals,
    )
    proposal = manager.agreements.create_proposal(
        team_id=resolved_team_id,
        phase_id=phase.phase_id,
        memory_item=rule_item,
        proposed_by=actor_id,
        reason_code="rule",
        approval_count_required=approvals_required,
        owner_override=_agreement_owner_override(trust_rules, agreement_defaults),
        ai_profile=ai.name,
    )
    events.append(
        build_proposed_event(
            ai_profile=ai.name,
            session=space_ctx.session_id,
            proposal=proposal,
            memory_id=rule_item.id,
            lane=lane,
        )
    )
    manager._cache.clear()
    return events


def apply_agreement_action(
    manager,
    ai: ir.AIDecl,
    state: Dict[str, object],
    request: AgreementRequest,
    *,
    identity: Dict[str, object] | None = None,
    project_root: str | None = None,
    app_path: str | None = None,
    team_id: str | None = None,
    agreement_defaults: dict | None = None,
) -> list[dict]:
    space_ctx = manager.space_context(
        state,
        identity=identity,
        project_root=project_root,
        app_path=app_path,
    )
    policy = manager.policy_for(ai)
    contract = manager.policy_contract_for(policy)
    phase_request = phase_request_from_state(state)
    session_key = space_ctx.store_key_for("session", lane="my")
    session_phase = manager._phases.current(session_key)
    resolved_team_id = team_id or resolve_team_id(project_root=project_root, app_path=app_path, config=None)
    events = apply_agreement_action_engine(
        ai_profile=ai.name,
        session=space_ctx.session_id,
        request=request,
        agreements=manager.agreements,
        team_id=resolved_team_id,
        space_ctx=space_ctx,
        policy=policy,
        contract=contract,
        short_term=manager.short_term,
        semantic=manager.semantic,
        profile=manager.profile,
        factory=manager._factory,
        phase_registry=manager._phases,
        phase_ledger=manager._ledger,
        phase_request=phase_request,
        session_phase=session_phase,
        identity=identity,
        state=state,
        budget_configs=manager._budgets,
        agreement_defaults=agreement_defaults,
    )
    manager._cache.clear()
    return events


def _agreement_approval_count(trust_rules, agreement_defaults: dict | None) -> int:
    if agreement_defaults and agreement_defaults.get("approval_count_required") is not None:
        return int(agreement_defaults.get("approval_count_required"))
    return required_approvals(trust_rules)


def _agreement_owner_override(trust_rules, agreement_defaults: dict | None) -> bool:
    if agreement_defaults and agreement_defaults.get("owner_override") is not None:
        return bool(agreement_defaults.get("owner_override"))
    return bool(getattr(trust_rules, "owner_override", True))


__all__ = ["apply_agreement_action", "propose_rule_with_events"]
