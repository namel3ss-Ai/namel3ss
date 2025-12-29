from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.identity.context import resolve_identity
import namel3ss.runtime.memory.api as memory_api
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.runtime.memory_rules import (
    ACTION_HANDOFF_REJECT,
    active_rules_for_scope,
    enforce_action,
)
from namel3ss.runtime.memory_rules.traces import build_rule_applied_event
from namel3ss.runtime.memory_trust import (
    actor_id_from_identity,
    build_trust_check_event,
    build_trust_rules_event,
    can_change_rules,
    can_handoff_reject,
    rules_from_contract,
    rules_from_state,
    trust_level_from_identity,
)
from namel3ss.runtime.memory_handoff import HANDOFF_STATUS_PENDING, build_handoff_rejected_event, build_packet_preview
from namel3ss.runtime.memory_explain import append_explanation_events
from namel3ss.secrets import collect_secret_values
from namel3ss.studio.session import SessionState


def get_handoff_payload(app_path: str, session: SessionState) -> dict:
    config = load_config(app_path=Path(app_path))
    source = Path(app_path).read_text(encoding="utf-8")
    program_ir = lower_program(parse(source))
    identity = resolve_identity(config, getattr(program_ir, "identity", None))
    session.memory_manager.ensure_restored(
        project_root=str(Path(app_path).parent),
        app_path=app_path,
    )
    team_id = resolve_team_id(project_root=str(Path(app_path).parent), app_path=app_path, config=config)
    packets = session.memory_manager.handoffs.list_packets(team_id)
    return {
        "ok": True,
        "team_id": team_id,
        "actor_id": actor_id_from_identity(identity),
        "agents": [_agent_payload(agent) for agent in program_ir.agents.values()],
        "packets": [_packet_payload(packet, session) for packet in packets],
    }


def create_handoff_payload(
    app_path: str,
    session: SessionState,
    *,
    from_agent_id: str,
    to_agent_id: str,
) -> dict:
    ai_profile, identity, team_id = _resolve_context(app_path)
    startup_events = session.memory_manager.startup_events(
        project_root=str(Path(app_path).parent),
        app_path=app_path,
    )
    events: list[dict] = list(startup_events)
    if not from_agent_id or not to_agent_id:
        raise Namel3ssError("Both from agent id and to agent id are required.")
    pack = memory_api.admin_action(
        session.memory_manager,
        ai_profile,
        session.state,
        "create_handoff",
        {"from_agent_id": from_agent_id, "to_agent_id": to_agent_id},
        identity=identity,
        project_root=str(Path(app_path).parent),
        app_path=app_path,
        team_id=team_id,
    )
    events.extend(pack.events)
    packet_id = None
    if isinstance(pack.payload, dict):
        packet_id = pack.payload.get("packet_id")
    if packet_id:
        secret_values = collect_secret_values(load_config(app_path=Path(app_path)))
        session.memory_manager.persist(
            project_root=str(Path(app_path).parent),
            app_path=app_path,
            secret_values=secret_values,
        )
    return _handoff_payload_with_traces(app_path, session, ai_profile, events)


def apply_handoff_payload(
    app_path: str,
    session: SessionState,
    *,
    packet_id: str,
) -> dict:
    ai_profile, identity, team_id = _resolve_context(app_path)
    startup_events = session.memory_manager.startup_events(
        project_root=str(Path(app_path).parent),
        app_path=app_path,
    )
    events: list[dict] = list(startup_events)
    packet = session.memory_manager.handoffs.get_packet(packet_id)
    if packet is None:
        raise Namel3ssError("Handoff packet was not found.")
    if packet.status != HANDOFF_STATUS_PENDING:
        raise Namel3ssError("Handoff packet is not pending.")
    pack = memory_api.admin_action(
        session.memory_manager,
        ai_profile,
        session.state,
        "apply_handoff",
        {"packet_id": packet_id},
        identity=identity,
        project_root=str(Path(app_path).parent),
        app_path=app_path,
        team_id=team_id,
    )
    events.extend(pack.events)
    applied_packet = session.memory_manager.handoffs.get_packet(packet_id)
    if applied_packet and applied_packet.status != HANDOFF_STATUS_PENDING:
        secret_values = collect_secret_values(load_config(app_path=Path(app_path)))
        session.memory_manager.persist(
            project_root=str(Path(app_path).parent),
            app_path=app_path,
            secret_values=secret_values,
        )
    return _handoff_payload_with_traces(app_path, session, ai_profile, events)


def reject_handoff_payload(
    app_path: str,
    session: SessionState,
    *,
    packet_id: str,
) -> dict:
    ai_profile, identity, team_id = _resolve_context(app_path)
    startup_events = session.memory_manager.startup_events(
        project_root=str(Path(app_path).parent),
        app_path=app_path,
    )
    events: list[dict] = list(startup_events)
    space_ctx = session.memory_manager.space_context(
        session.state,
        identity=identity,
        project_root=str(Path(app_path).parent),
        app_path=app_path,
    )
    packet = session.memory_manager.handoffs.get_packet(packet_id)
    if packet is None:
        raise Namel3ssError("Handoff packet was not found.")
    if packet.status != HANDOFF_STATUS_PENDING:
        raise Namel3ssError("Handoff packet is not pending.")
    policy = session.memory_manager.policy_for(ai_profile)
    contract = session.memory_manager.policy_contract_for(policy)
    actor_level = trust_level_from_identity(identity)
    actor_id = actor_id_from_identity(identity)
    trust_rules, trust_events = _resolve_trust_rules(
        ai_profile=ai_profile.name,
        session_id=space_ctx.session_id,
        team_id=team_id,
        actor_id=actor_id,
        actor_level=actor_level,
        state=session.state,
        contract=contract,
    )
    events.extend(trust_events)
    team_rules = active_rules_for_scope(semantic=session.memory_manager.semantic, space_ctx=space_ctx, scope="team")
    rule_check = enforce_action(
        rules=team_rules,
        action=ACTION_HANDOFF_REJECT,
        actor_level=actor_level,
        event_type="context",
    )
    events.extend(_rule_events(ai_profile.name, space_ctx.session_id, rule_check))
    if not rule_check.allowed:
        return _handoff_payload_with_traces(app_path, session, ai_profile, events)
    decision = can_handoff_reject(actor_level, trust_rules)
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
        return _handoff_payload_with_traces(app_path, session, ai_profile, events)
    session.memory_manager.handoffs.reject_packet(packet.packet_id)
    secret_values = collect_secret_values(load_config(app_path=Path(app_path)))
    session.memory_manager.persist(
        project_root=str(Path(app_path).parent),
        app_path=app_path,
        secret_values=secret_values,
    )
    events.append(build_handoff_rejected_event(ai_profile=ai_profile.name, session=space_ctx.session_id, packet=packet))
    return _handoff_payload_with_traces(app_path, session, ai_profile, events)


def _handoff_payload_with_traces(app_path: str, session: SessionState, ai_profile, events: list[dict]) -> dict:
    events = append_explanation_events(events)
    traces = []
    if events:
        traces.append(
            {
                "ai_name": ai_profile.name,
                "ai_profile_name": ai_profile.name,
                "agent_name": None,
                "model": ai_profile.model,
                "system_prompt": ai_profile.system_prompt,
                "input": "",
                "output": "",
                "memory": {},
                "tool_calls": [],
                "tool_results": [],
                "canonical_events": events,
            }
        )
    payload = get_handoff_payload(app_path, session)
    payload["traces"] = traces
    return payload


def _resolve_context(app_path: str):
    config = load_config(app_path=Path(app_path))
    source = Path(app_path).read_text(encoding="utf-8")
    program_ir = lower_program(parse(source))
    if not program_ir.ais:
        raise Namel3ssError("No AI profile available for handoff.")
    ai_profile = next(iter(program_ir.ais.values()))
    identity = resolve_identity(config, getattr(program_ir, "identity", None))
    team_id = resolve_team_id(project_root=str(Path(app_path).parent), app_path=app_path, config=config)
    return ai_profile, identity, team_id


def _resolve_trust_rules(
    *,
    ai_profile: str,
    session_id: str,
    team_id: str,
    actor_id: str,
    actor_level: str,
    state: dict | None,
    contract,
) -> tuple[object, list[dict]]:
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


def _agent_payload(agent) -> dict:
    return {
        "agent_id": agent.name,
        "name": agent.name,
        "ai_name": agent.ai_name,
    }


def _packet_payload(packet, session: SessionState) -> dict:
    preview = build_packet_preview(
        short_term=session.memory_manager.short_term,
        semantic=session.memory_manager.semantic,
        profile=session.memory_manager.profile,
        item_ids=packet.items,
    )
    return {
        "packet_id": packet.packet_id,
        "from_agent_id": packet.from_agent_id,
        "to_agent_id": packet.to_agent_id,
        "team_id": packet.team_id,
        "space": packet.space,
        "phase_id": packet.phase_id,
        "created_by": packet.created_by,
        "created_at": packet.created_at,
        "status": packet.status,
        "item_count": len(packet.items),
        "summary_lines": list(packet.summary_lines),
        "previews": preview,
    }


__all__ = [
    "apply_handoff_payload",
    "create_handoff_payload",
    "get_handoff_payload",
    "reject_handoff_payload",
]
