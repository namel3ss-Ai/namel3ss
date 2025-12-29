from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.contract import normalize_memory_item
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory.events import EVENT_CONTEXT
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.runtime.memory_lanes.model import LANE_AGENT, LANE_TEAM, agent_lane_key
from namel3ss.runtime.memory.spaces import SPACE_PROJECT, SPACE_SESSION
from namel3ss.runtime.memory.write_engine.phases import _ensure_phase_for_store
from namel3ss.runtime.memory_agreement import AgreementRequest
from namel3ss.runtime.memory_handoff import (
    HANDOFF_STATUS_PENDING,
    apply_handoff_packet,
    briefing_lines,
    build_agent_briefing_event,
    build_handoff_applied_event,
    build_handoff_created_event,
    build_handoff_rejected_event,
    select_handoff_items,
)
from namel3ss.runtime.memory_rules import (
    ACTION_HANDOFF_APPLY,
    ACTION_HANDOFF_CREATE,
    ACTION_HANDOFF_REJECT,
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
    can_handoff_reject,
    rules_from_contract,
    rules_from_state,
    trust_level_from_identity,
)
from namel3ss.runtime.memory_impact import ImpactResult

from .scenario import Scenario, ScenarioStep


@dataclass
class ScenarioRun:
    scenario_id: str
    scenario_name: str
    recall_steps: list[dict]
    write_steps: list[dict]
    meta: dict


def run_scenario(scenario: Scenario) -> ScenarioRun:
    manager = MemoryManager()
    state = deepcopy(scenario.initial_state)
    identity = deepcopy(scenario.identity)
    ai_profile = _build_ai_profile(scenario.ai_profile)
    recall_steps: list[dict] = []
    write_steps: list[dict] = []
    recall_hashes: list[dict] = []
    cache_versions_by_step: list[dict] = []
    phase_snapshots_by_step: list[dict] = []
    memory_snapshot = _snapshot_memory_items(manager)

    for step_index, step in enumerate(scenario.steps, start=1):
        if step.kind == "recall":
            recall_step = _run_recall_step(
                manager,
                ai_profile,
                step,
                state=state,
                identity=identity,
                step_index=step_index,
            )
            recall_steps.append(recall_step)
            recall_hashes.append(
                {
                    "step_index": step_index,
                    "deterministic_hash": recall_step.get("deterministic_hash"),
                }
            )
        elif step.kind == "record":
            write_steps.append(
                _run_record_step(
                    manager,
                    ai_profile,
                    step,
                    state=state,
                    identity=identity,
                    step_index=step_index,
                )
            )
        elif step.kind == "admin":
            before_snapshot = memory_snapshot
            admin_step = _run_admin_step(
                manager,
                ai_profile,
                step,
                state=state,
                identity=identity,
                step_index=step_index,
            )
            after_snapshot = _snapshot_memory_items(manager)
            if "written" not in admin_step:
                admin_step["written"] = _delta_written(before_snapshot, after_snapshot)
            write_steps.append(admin_step)
        else:
            raise Namel3ssError(f"Unknown scenario step type: {step.kind}")
        cache_versions_by_step.append(
            {
                "step_index": step_index,
                "versions": _cache_versions(manager),
            }
        )
        phase_snapshots_by_step.append(
            {
                "step_index": step_index,
                "phases": _phase_snapshot(manager),
            }
        )
        memory_snapshot = _snapshot_memory_items(manager)

    meta = {
        "scenario": {
            "id": scenario.scenario_id,
            "name": scenario.name,
        },
        "step_counts": {
            "total": len(scenario.steps),
            "recall": len(recall_steps),
            "record": len([step for step in scenario.steps if step.kind == "record"]),
            "admin": len([step for step in scenario.steps if step.kind == "admin"]),
        },
        "memory_counts": _memory_counts(manager),
        "recall_hashes": recall_hashes,
        "cache_versions_by_step": cache_versions_by_step,
        "phase_snapshots_by_step": phase_snapshots_by_step,
    }
    return ScenarioRun(
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
        recall_steps=recall_steps,
        write_steps=write_steps,
        meta=meta,
    )


def _run_recall_step(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    step: ScenarioStep,
    *,
    state: dict,
    identity: dict,
    step_index: int,
) -> dict:
    payload = step.payload
    user_input = payload.get("input")
    agent_id = payload.get("agent_id")
    context, events, meta = manager.recall_context_with_events(
        ai_profile,
        str(user_input),
        state,
        identity=identity,
        agent_id=str(agent_id) if agent_id else None,
    )
    recalled = _flatten_context(context)
    deterministic_hash = manager.recall_hash(recalled)
    return {
        "step_index": step_index,
        "step_kind": "recall",
        "input": user_input,
        "agent_id": agent_id,
        "context": context,
        "events": events,
        "meta": meta,
        "deterministic_hash": deterministic_hash,
    }


def _run_record_step(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    step: ScenarioStep,
    *,
    state: dict,
    identity: dict,
    step_index: int,
) -> dict:
    payload = step.payload
    user_input = payload.get("input")
    ai_output = payload.get("output")
    tool_events = payload.get("tool_events", []) or []
    agent_id = payload.get("agent_id")
    written, events = manager.record_interaction_with_events(
        ai_profile,
        state,
        str(user_input),
        str(ai_output),
        list(tool_events),
        identity=identity,
        agent_id=str(agent_id) if agent_id else None,
    )
    return {
        "step_index": step_index,
        "step_kind": "record",
        "input": user_input,
        "output": ai_output,
        "tool_events": tool_events,
        "agent_id": agent_id,
        "written": written,
        "events": events,
    }


def _run_admin_step(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    step: ScenarioStep,
    *,
    state: dict,
    identity: dict,
    step_index: int,
) -> dict:
    payload = step.payload
    action = payload.get("action")
    action_payload = payload.get("payload") or {}
    base = {
        "step_index": step_index,
        "step_kind": "admin",
        "action": action,
        "payload": action_payload,
    }
    if action == "propose_rule":
        events = _propose_rule(manager, ai_profile, state, identity, action_payload)
        base["events"] = events
        return base
    if action == "apply_agreement":
        events = _apply_agreement(manager, ai_profile, state, identity, action_payload)
        base["events"] = events
        return base
    if action == "create_handoff":
        events, packet = _create_handoff(manager, ai_profile, state, identity, action_payload)
        base["events"] = events
        if packet:
            base["result"] = {"packet_id": packet.packet_id, "status": packet.status}
        return base
    if action == "apply_handoff":
        events, applied = _apply_handoff(manager, ai_profile, state, identity, action_payload)
        base["events"] = events
        base["written"] = applied
        return base
    if action == "compute_impact":
        impact = _compute_impact(manager, action_payload)
        base["result"] = impact
        base["events"] = []
        return base
    if action == "advance_phase":
        state_update = _advance_phase(state, action_payload, step_index=step_index)
        base["result"] = {"state_update": state_update}
        base["events"] = []
        return base
    raise Namel3ssError(f"Unsupported admin action: {action}")


def _build_ai_profile(spec) -> ir.AIDecl:
    memory = ir.AIMemory(
        short_term=int(spec.memory.short_term),
        semantic=bool(spec.memory.semantic),
        profile=bool(spec.memory.profile),
        line=1,
        column=1,
    )
    return ir.AIDecl(
        name=spec.name,
        model=spec.model,
        provider=spec.provider,
        system_prompt=spec.system_prompt,
        exposed_tools=list(spec.exposed_tools),
        memory=memory,
        line=1,
        column=1,
    )


def _flatten_context(context: dict) -> list[dict]:
    return list(context.get("short_term", [])) + list(context.get("semantic", [])) + list(context.get("profile", []))


def _propose_rule(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    identity: dict,
    payload: dict,
) -> list[dict]:
    text = payload.get("text")
    if not text:
        raise Namel3ssError("propose_rule requires payload.text")
    scope = payload.get("scope") or "team"
    priority = int(payload.get("priority", 0))
    requested_by = payload.get("requested_by") or "user"
    request = RuleRequest(text=str(text), scope=str(scope), priority=priority, requested_by=str(requested_by))
    return manager.propose_rule_with_events(ai_profile, state, request, identity=identity)


def _apply_agreement(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    identity: dict,
    payload: dict,
) -> list[dict]:
    action = payload.get("action")
    if action not in {"approve", "reject"}:
        raise Namel3ssError("apply_agreement requires payload.action approve|reject")
    proposal_id = payload.get("proposal_id")
    team_id = resolve_team_id(project_root=None, app_path=None, config=None)
    if proposal_id in {None, "", "first_pending", "auto"}:
        proposal = manager.agreements.select_pending(team_id, None)
        proposal_id = proposal.proposal_id if proposal else None
    request = AgreementRequest(
        action=str(action),
        proposal_id=str(proposal_id) if proposal_id else None,
        requested_by=str(payload.get("requested_by") or "user"),
    )
    return manager.apply_agreement_action(ai_profile, state, request, identity=identity)


def _create_handoff(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    identity: dict,
    payload: dict,
) -> tuple[list[dict], object | None]:
    from_agent_id = payload.get("from_agent_id")
    to_agent_id = payload.get("to_agent_id")
    if not from_agent_id or not to_agent_id:
        raise Namel3ssError("create_handoff requires payload.from_agent_id and payload.to_agent_id")
    space_ctx = manager.space_context(state, identity=identity)
    policy = manager.policy_for(ai_profile)
    contract = manager.policy_contract_for(policy)
    team_id = resolve_team_id(project_root=None, app_path=None, config=None)
    actor_level = trust_level_from_identity(identity)
    actor_id = actor_id_from_identity(identity)
    trust_rules, trust_events = _resolve_trust_rules(
        ai_profile=ai_profile.name,
        session_id=space_ctx.session_id,
        team_id=team_id,
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
        proposals=manager.agreements.list_pending(team_id),
        rules=team_rules,
    )
    summary_lines = briefing_lines(selection)
    phase_id = _handoff_phase_id(manager, from_key, team_key)
    packet = manager.handoffs.create_packet(
        from_agent_id=str(from_agent_id),
        to_agent_id=str(to_agent_id),
        team_id=team_id,
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
    identity: dict,
    payload: dict,
) -> tuple[list[dict], list[dict]]:
    packet_id = payload.get("packet_id")
    team_id = resolve_team_id(project_root=None, app_path=None, config=None)
    if packet_id in {None, "", "first_pending", "auto"}:
        pending = manager.handoffs.list_packets(team_id)
        packet_id = pending[0].packet_id if pending else None
    if not packet_id:
        raise Namel3ssError("apply_handoff requires payload.packet_id")
    packet = manager.handoffs.get_packet(str(packet_id))
    if packet is None:
        raise Namel3ssError("Handoff packet was not found.")
    if packet.status != HANDOFF_STATUS_PENDING:
        raise Namel3ssError("Handoff packet is not pending.")
    space_ctx = manager.space_context(state, identity=identity)
    policy = manager.policy_for(ai_profile)
    contract = manager.policy_contract_for(policy)
    actor_level = trust_level_from_identity(identity)
    actor_id = actor_id_from_identity(identity)
    trust_rules, trust_events = _resolve_trust_rules(
        ai_profile=ai_profile.name,
        session_id=space_ctx.session_id,
        team_id=team_id,
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


def _advance_phase(state: dict, payload: dict, *, step_index: int) -> dict:
    token = payload.get("token") or f"proof-phase-{step_index}"
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
            events.append(
                build_rule_applied_event(
                    ai_profile=ai_profile,
                    session=session_id,
                    applied=applied,
                )
            )
    return events


def _handoff_phase_id(manager: MemoryManager, agent_key: str, team_key: str) -> str:
    phase = manager._phases.current(agent_key)
    if phase is None:
        phase = manager._phases.current(team_key)
    return phase.phase_id if phase else "phase-unknown"


def _snapshot_memory_items(manager: MemoryManager) -> dict[str, dict]:
    items: dict[str, dict] = {}
    for item in manager.short_term.all_items():
        data = normalize_memory_item(item)
        items[data["id"]] = data
    for item in manager.semantic.all_items():
        data = normalize_memory_item(item)
        items[data["id"]] = data
    for item in manager.profile.all_items():
        data = normalize_memory_item(item)
        items[data["id"]] = data
    return items


def _delta_written(before: dict[str, dict], after: dict[str, dict]) -> list[dict]:
    added: list[dict] = []
    for memory_id, item in after.items():
        if memory_id not in before:
            added.append(item)
    added.sort(key=lambda entry: entry.get("id") or "")
    return added


def _cache_versions(manager: MemoryManager) -> list[dict]:
    versions: list[dict] = []
    for (store_key, kind), version in getattr(manager, "_cache_versions", {}).items():
        versions.append({"store_key": str(store_key), "kind": str(kind), "version": int(version)})
    versions.sort(key=lambda entry: (entry["store_key"], entry["kind"]))
    return versions


def _phase_snapshot(manager: MemoryManager) -> list[dict]:
    phases: list[dict] = []
    registry = getattr(manager, "_phases", None)
    if registry is None:
        return phases
    current_map = getattr(registry, "_current", {})
    history_map = getattr(registry, "_history", {})
    for store_key, current in current_map.items():
        history = history_map.get(store_key, [])
        phases.append(
            {
                "store_key": store_key,
                "current_phase_id": current.phase_id if current else None,
                "history_ids": [phase.phase_id for phase in history],
            }
        )
    phases.sort(key=lambda entry: entry["store_key"])
    return phases


def _memory_counts(manager: MemoryManager) -> dict:
    return {
        "short_term": len(manager.short_term.all_items()),
        "semantic": len(manager.semantic.all_items()),
        "profile": len(manager.profile.all_items()),
    }


__all__ = ["ScenarioRun", "run_scenario"]
