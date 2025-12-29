from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.memory_explain import append_explanation_events
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.runtime.memory_rules import (
    RuleRequest,
    active_rules_for_store,
    pending_rules_from_proposals,
    rule_lane_for_scope,
    rule_space_for_scope,
)
from namel3ss.runtime.memory_trust import actor_id_from_identity
from namel3ss.secrets import collect_secret_values
from namel3ss.studio.session import SessionState


def get_rules_payload(app_path: str, session: SessionState) -> dict:
    config = load_config(app_path=Path(app_path))
    source = Path(app_path).read_text(encoding="utf-8")
    program_ir = lower_program(parse(source))
    identity = resolve_identity(config, getattr(program_ir, "identity", None))
    session.memory_manager.ensure_restored(
        project_root=str(Path(app_path).parent),
        app_path=app_path,
    )
    team_id = resolve_team_id(project_root=str(Path(app_path).parent), app_path=app_path, config=config)
    space_ctx = session.memory_manager.space_context(
        session.state,
        identity=identity,
        project_root=str(Path(app_path).parent),
        app_path=app_path,
    )
    team_store_key = space_ctx.store_key_for(rule_space_for_scope("team"), lane=rule_lane_for_scope("team"))
    system_store_key = space_ctx.store_key_for(rule_space_for_scope("system"), lane=rule_lane_for_scope("system"))
    semantic = session.memory_manager.semantic
    active_team = active_rules_for_store(semantic.items_for_store(team_store_key))
    active_system = active_rules_for_store(semantic.items_for_store(system_store_key))
    proposals = session.memory_manager.agreements.list_pending(team_id)
    pending_team = pending_rules_from_proposals(proposals, scope="team")
    pending_system = pending_rules_from_proposals(proposals, scope="system")
    return {
        "ok": True,
        "team_id": team_id,
        "active_team": [_rule_payload(rule) for rule in active_team],
        "active_system": [_rule_payload(rule) for rule in active_system],
        "pending_team": [_rule_payload(rule) for rule in pending_team],
        "pending_system": [_rule_payload(rule) for rule in pending_system],
        "actor_id": actor_id_from_identity(identity),
    }


def propose_rule_payload(
    app_path: str,
    session: SessionState,
    *,
    text: str,
    scope: str,
    priority: int = 0,
) -> dict:
    config = load_config(app_path=Path(app_path))
    source = Path(app_path).read_text(encoding="utf-8")
    program_ir = lower_program(parse(source))
    if not program_ir.ais:
        raise Namel3ssError("No AI profile available for rules.")
    ai_profile = next(iter(program_ir.ais.values()))
    identity = resolve_identity(config, getattr(program_ir, "identity", None))
    team_id = resolve_team_id(project_root=str(Path(app_path).parent), app_path=app_path, config=config)
    actor_id = actor_id_from_identity(identity)
    request = RuleRequest(text=text, scope=scope, priority=priority, requested_by=actor_id)
    events = session.memory_manager.propose_rule_with_events(
        ai_profile,
        session.state,
        request,
        identity=identity,
        project_root=str(Path(app_path).parent),
        app_path=app_path,
        team_id=team_id,
    )
    secret_values = collect_secret_values(config)
    session.memory_manager.persist(
        project_root=str(Path(app_path).parent),
        app_path=app_path,
        secret_values=secret_values,
    )
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
    payload = get_rules_payload(app_path, session)
    payload["traces"] = traces
    return payload


def _rule_payload(rule) -> dict:
    return {
        "rule_id": rule.rule_id,
        "text": rule.text,
        "scope": rule.scope,
        "lane": rule.lane,
        "phase_id": rule.phase_id,
        "status": rule.status,
        "created_by": rule.created_by,
        "created_at": rule.created_at,
        "priority": rule.priority,
        "proposal_id": rule.proposal_id,
    }


__all__ = ["get_rules_payload", "propose_rule_payload"]
