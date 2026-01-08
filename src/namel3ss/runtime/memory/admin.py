from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.contract import normalize_memory_item
from namel3ss.runtime.memory.events import EVENT_CONTEXT
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory.spaces import SPACE_PROJECT
from namel3ss.runtime.memory_agreement import AgreementRequest
from namel3ss.runtime.memory_handoff import (
    HANDOFF_STATUS_PENDING,
    apply_handoff_packet,
    briefing_lines,
    build_agent_briefing_event,
    build_handoff_applied_event,
    build_handoff_created_event,
    select_handoff_items,
)
from namel3ss.runtime.memory_impact.model import ImpactResult
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_TEAM, agent_lane_key
from namel3ss.runtime.memory_rules import (
    ACTION_HANDOFF_APPLY,
    ACTION_HANDOFF_CREATE,
    RuleRequest,
    active_rules_for_scope,
    enforce_action,
)
from namel3ss.runtime.memory_rules.traces import build_rule_applied_event
from namel3ss.runtime.memory_trust import (
    actor_id_from_identity,
    build_trust_check_event,
    build_trust_rules_event,
    can_change_rules,
    can_handoff_apply,
    can_handoff_create,
    rules_from_contract,
    rules_from_state,
    trust_level_from_identity,
)
from namel3ss.runtime.memory.write_engine.phases import _ensure_phase_for_store


def run_admin_action(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    action: str,
    payload: dict | None = None,
    *,
    identity: dict | None = None,
    project_root: str | None = None,
    app_path: str | None = None,
    team_id: str | None = None,
) -> tuple[object, list[dict]]:
    payload = payload or {}
    if action == "propose_rule":
        return {}, _propose_rule(manager, ai_profile, state, identity, payload, project_root, app_path)
    if action == "apply_agreement":
        return {}, _apply_agreement(manager, ai_profile, state, identity, payload, project_root, app_path, team_id)
    if action == "create_handoff":
        events, packet = _create_handoff(manager, ai_profile, state, identity, payload, project_root, app_path, team_id)
        result = {"packet_id": getattr(packet, "packet_id", None), "status": getattr(packet, "status", None)}
        return result, events
    if action == "apply_handoff":
        events, written = _apply_handoff(manager, ai_profile, state, identity, payload, project_root, app_path, team_id)
        return {"written": written}, events
    if action == "compute_impact":
        return _compute_impact(manager, payload), []
    if action == "advance_phase":
        return {"state_update": _advance_phase(state, payload)}, []
    raise Namel3ssError(f"Unsupported admin action: {action}")


def _propose_rule(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    identity: dict | None,
    payload: dict,
    project_root: str | None,
    app_path: str | None,
) -> list[dict]:
    text = payload.get("text")
    if not text:
        raise Namel3ssError("propose_rule requires payload.text")
    scope = payload.get("scope") or "team"
    priority = int(payload.get("priority", 0))
    requested_by = payload.get("requested_by") or "user"
    request = RuleRequest(text=str(text), scope=str(scope), priority=priority, requested_by=str(requested_by))
    return manager.propose_rule_with_events(
        ai_profile,
        state,
        request,
        identity=identity,
        project_root=project_root,
        app_path=app_path,
    )


def _apply_agreement(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    identity: dict | None,
    payload: dict,
    project_root: str | None,
    app_path: str | None,
    team_id: str | None,
) -> list[dict]:
    action = payload.get("action")
    if action not in {"approve", "reject"}:
        raise Namel3ssError("apply_agreement requires payload.action approve|reject")
    proposal_id = payload.get("proposal_id")
    resolved_team_id = team_id or resolve_team_id(project_root=project_root, app_path=app_path, config=None)
    if proposal_id in {None, "", "first_pending", "auto"}:
        proposal = manager.agreements.select_pending(resolved_team_id, None)
        proposal_id = proposal.proposal_id if proposal else None
    request = AgreementRequest(
        action=str(action),
        proposal_id=str(proposal_id) if proposal_id else None,
        requested_by=str(payload.get("requested_by") or "user"),
    )
    return manager.apply_agreement_action(
        ai_profile,
        state,
        request,
        identity=identity,
        project_root=project_root,
        app_path=app_path,
        team_id=resolved_team_id,
    )


def _create_handoff(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    identity: dict | None,
    payload: dict,
    project_root: str | None,
    app_path: str | None,
    team_id: str | None,
) -> tuple[list[dict], object | None]:
    from_agent_id = payload.get("from_agent_id")
    to_agent_id = payload.get("to_agent_id")
    if not from_agent_id or not to_agent_id:
        raise Namel3ssError("create_handoff requires payload.from_agent_id and payload.to_agent_id")
    space_ctx = manager.space_context(state, identity=identity, project_root=project_root, app_path=app_path)
    policy = manager.policy_for(ai_profile)
    contract = manager.policy_contract_for(policy)
    resolved_team_id = team_id or resolve_team_id(project_root=project_root, app_path=app_path, config=None)
    actor_level = trust_level_from_identity(identity)
    actor_id = actor_id_from_identity(identity)
    trust_rules, trust_events = _resolve_trust_rules(
        ai_profile=ai_profile.name,
        session_id=space_ctx.session_id,
        team_id=resolved_team_id,
        actor_id=actor_id,
        actor_level=actor_level,
        state=state,
        contract=contract,
    )
    events = list(trust_events)
    team_rules = active_rules_for_scope(semantic=manager.semantic, space_ctx=space_ctx, scope="team")
    rule_check = enforce_action(
        rules=team_rules,
        action=ACTION_HANDOFF_CREATE,
        actor_level=actor_level,
        event_type=EVENT_CONTEXT,
    )
    events.extend(_rule_events(ai_profile.name, space_ctx.session_id, rule_check))
    if not rule_check.allowed:
        return events, None
    decision = can_handoff_create(actor_level, trust_rules)
    events.append(
        build_trust_check_event(
            ai_profile=ai_profile.name,
            session=space_ctx.session_id,
            action=decision.action,
            actor_id=actor_id,
            actor_level=decision.actor_level,
            required_level=decision.required_level,
            allowed=decision.allowed,
            reason=decision.reason,
        )
    )
    if not decision.allowed:
        return events, None
    from_key = agent_lane_key(space_ctx, space=SPACE_PROJECT, agent_id=str(from_agent_id))
    team_key = space_ctx.store_key_for(SPACE_PROJECT, lane=LANE_TEAM)
    selection = select_handoff_items(
        agent_items=manager.semantic.items_for_store(from_key),
        team_items=manager.semantic.items_for_store(team_key),
        proposals=manager.agreements.list_pending(resolved_team_id),
        rules=team_rules,
    )
    summary_lines = briefing_lines(selection)
    phase_id = _handoff_phase_id(manager, from_key, team_key)
    packet = manager.handoffs.create_packet(
        from_agent_id=str(from_agent_id),
        to_agent_id=str(to_agent_id),
        team_id=resolved_team_id,
        space=SPACE_PROJECT,
        phase_id=phase_id,
        created_by=actor_id,
        items=selection.item_ids,
        summary_lines=summary_lines,
    )
    events.append(build_handoff_created_event(ai_profile=ai_profile.name, session=space_ctx.session_id, packet=packet))
    return events, packet


def _apply_handoff(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    identity: dict | None,
    payload: dict,
    project_root: str | None,
    app_path: str | None,
    team_id: str | None,
) -> tuple[list[dict], list[dict]]:
    packet_id = payload.get("packet_id")
    resolved_team_id = team_id or resolve_team_id(project_root=project_root, app_path=app_path, config=None)
    if packet_id in {None, "", "first_pending", "auto"}:
        pending = manager.handoffs.list_packets(resolved_team_id)
        packet_id = pending[0].packet_id if pending else None
    if not packet_id:
        raise Namel3ssError("apply_handoff requires payload.packet_id")
    packet = manager.handoffs.get_packet(str(packet_id))
    if packet is None:
        raise Namel3ssError("Handoff packet was not found.")
    if packet.status != HANDOFF_STATUS_PENDING:
        raise Namel3ssError("Handoff packet is not pending.")
    space_ctx = manager.space_context(state, identity=identity, project_root=project_root, app_path=app_path)
    policy = manager.policy_for(ai_profile)
    contract = manager.policy_contract_for(policy)
    actor_level = trust_level_from_identity(identity)
    actor_id = actor_id_from_identity(identity)
    trust_rules, trust_events = _resolve_trust_rules(
        ai_profile=ai_profile.name,
        session_id=space_ctx.session_id,
        team_id=resolved_team_id,
        actor_id=actor_id,
        actor_level=actor_level,
        state=state,
        contract=contract,
    )
    events = list(trust_events)
    team_rules = active_rules_for_scope(semantic=manager.semantic, space_ctx=space_ctx, scope="team")
    rule_check = enforce_action(
        rules=team_rules,
        action=ACTION_HANDOFF_APPLY,
        actor_level=actor_level,
        event_type=EVENT_CONTEXT,
    )
    events.extend(_rule_events(ai_profile.name, space_ctx.session_id, rule_check))
    if not rule_check.allowed:
        return events, []
    decision = can_handoff_apply(actor_level, trust_rules)
    events.append(
        build_trust_check_event(
            ai_profile=ai_profile.name,
            session=space_ctx.session_id,
            action=decision.action,
            actor_id=actor_id,
            actor_level=decision.actor_level,
            required_level=decision.required_level,
            allowed=decision.allowed,
            reason=decision.reason,
        )
    )
    if not decision.allowed:
        return events, []
    target_key = agent_lane_key(space_ctx, space=packet.space, agent_id=packet.to_agent_id)
    target_owner = space_ctx.owner_for(packet.space)
    target_phase, phase_events = _ensure_phase_for_store(
        ai_profile=ai_profile.name,
        session=space_ctx.session_id,
        space=packet.space,
        owner=target_owner,
        store_key=target_key,
        contract=contract,
        phase_registry=manager._phases,
        phase_ledger=manager._ledger,
        request=None,
        default_reason="handoff",
        lane=LANE_AGENT,
    )
    events.extend(phase_events)
    applied_items = apply_handoff_packet(
        packet=packet,
        short_term=manager.short_term,
        semantic=manager.semantic,
        profile=manager.profile,
        factory=manager._factory,
        target_store_key=target_key,
        target_phase=target_phase,
        space=packet.space,
        owner=target_owner,
        agent_id=packet.to_agent_id,
        allow_team_change=contract.lanes.team_can_change,
        phase_ledger=manager._ledger,
        dedupe_enabled=policy.dedupe_enabled,
        authority_order=contract.authority_order,
    )
    manager.handoffs.apply_packet(packet.packet_id)
    events.append(
        build_handoff_applied_event(
            ai_profile=ai_profile.name,
            session=space_ctx.session_id,
            packet=packet,
            item_count=len(applied_items),
            applied_items=applied_items,
        )
    )
    events.append(build_agent_briefing_event(ai_profile=ai_profile.name, session=space_ctx.session_id, packet=packet))
    return events, [normalize_memory_item(item) for item in applied_items]


def _compute_impact(manager: MemoryManager, payload: dict) -> dict:
    memory_id = payload.get("memory_id")
    if not memory_id:
        raise Namel3ssError("compute_impact requires payload.memory_id")
    depth_limit = int(payload.get("depth_limit", 2))
    max_items = int(payload.get("max_items", 10))
    result = manager.compute_impact(str(memory_id), depth_limit=depth_limit, max_items=max_items)
    if not isinstance(result, ImpactResult):
        return {"title": "impact", "items": [], "lines": []}
    return {
        "title": result.title,
        "items": [item.__dict__ for item in result.items],
        "lines": list(result.lines),
        "path_lines": list(result.path_lines),
    }


def _advance_phase(state: dict, payload: dict) -> dict:
    token = payload.get("token") or "manual"
    state["_memory_phase_token"] = str(token)
    if payload.get("name") is not None:
        state["_memory_phase_name"] = str(payload.get("name"))
    if payload.get("reason") is not None:
        state["_memory_phase_reason"] = str(payload.get("reason"))
    if payload.get("diff_from") is not None:
        state["_memory_phase_diff_from"] = str(payload.get("diff_from"))
    if payload.get("diff_to") is not None:
        state["_memory_phase_diff_to"] = str(payload.get("diff_to"))
    if payload.get("diff_space") is not None:
        state["_memory_phase_diff_space"] = str(payload.get("diff_space"))
    if payload.get("diff_lane") is not None:
        state["_memory_phase_diff_lane"] = str(payload.get("diff_lane"))
    return {
        "_memory_phase_token": state.get("_memory_phase_token"),
        "_memory_phase_name": state.get("_memory_phase_name"),
        "_memory_phase_reason": state.get("_memory_phase_reason"),
        "_memory_phase_diff_from": state.get("_memory_phase_diff_from"),
        "_memory_phase_diff_to": state.get("_memory_phase_diff_to"),
        "_memory_phase_diff_space": state.get("_memory_phase_diff_space"),
        "_memory_phase_diff_lane": state.get("_memory_phase_diff_lane"),
    }


def _resolve_trust_rules(*, ai_profile: str, session_id: str, team_id: str, actor_id: str, actor_level: str, state: dict, contract):
    trust_rules = rules_from_contract(contract)
    override_rules = rules_from_state(state, trust_rules)
    if override_rules is None:
        return trust_rules, []
    decision = can_change_rules(actor_level, trust_rules)
    events = [
        build_trust_check_event(
            ai_profile=ai_profile,
            session=session_id,
            action=decision.action,
            actor_id=actor_id,
            actor_level=decision.actor_level,
            required_level=decision.required_level,
            allowed=decision.allowed,
            reason=decision.reason,
        )
    ]
    if decision.allowed:
        trust_rules = override_rules
        events.append(
            build_trust_rules_event(
                ai_profile=ai_profile,
                session=session_id,
                team_id=team_id,
                rules=trust_rules,
            )
        )
    return trust_rules, events


def _rule_events(ai_profile: str, session_id: str, rule_check) -> list[dict]:
    events: list[dict] = []
    if rule_check.applied:
        for applied in rule_check.applied:
            events.append(build_rule_applied_event(ai_profile=ai_profile, session=session_id, applied=applied))
    return events


def _handoff_phase_id(manager: MemoryManager, agent_key: str, team_key: str) -> str:
    phase = manager._phases.current(agent_key)
    if phase is None:
        phase = manager._phases.current(team_key)
    return phase.phase_id if phase else "phase-unknown"


__all__ = ["run_admin_action"]
