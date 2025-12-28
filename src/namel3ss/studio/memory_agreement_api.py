from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.memory_agreement import AgreementRequest, ACTION_APPROVE, ACTION_REJECT
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.runtime.memory_explain import append_explanation_events
from namel3ss.runtime.memory_trust import (
    actor_id_from_identity,
    can_change_rules,
    rules_from_state,
    trust_level_from_identity,
    trust_overview_lines,
)
from namel3ss.studio.session import SessionState


def get_agreements_payload(app_path: str, session: SessionState) -> dict:
    config = load_config(app_path=Path(app_path))
    source = Path(app_path).read_text(encoding="utf-8")
    program_ir = lower_program(parse(source))
    team_id = resolve_team_id(project_root=str(Path(app_path).parent), app_path=app_path, config=config)
    proposals = session.memory_manager.list_team_proposals(team_id)
    ai_profile = next(iter(program_ir.ais.values()), None)
    trust_payload = {}
    if ai_profile is not None:
        policy = session.memory_manager.policy_for(ai_profile)
        contract = session.memory_manager.policy_contract_for(policy)
        identity = resolve_identity(config, getattr(program_ir, "identity", None))
        actor_id = actor_id_from_identity(identity)
        actor_level = trust_level_from_identity(identity)
        trust_rules = contract.trust
        override_rules = rules_from_state(session.state, trust_rules)
        if override_rules is not None:
            decision = can_change_rules(actor_level, trust_rules)
            if decision.allowed:
                trust_rules = override_rules
        trust_payload = {
            "actor_id": actor_id,
            "actor_level": actor_level,
            "rules": trust_rules.as_dict(),
            "lines": trust_overview_lines(actor_id=actor_id, actor_level=actor_level, rules=trust_rules),
        }
    return {"ok": True, "team_id": team_id, "proposals": proposals, "trust": trust_payload}


def apply_agreement_action_payload(
    app_path: str,
    session: SessionState,
    *,
    action: str,
    proposal_id: str | None,
) -> dict:
    if action not in {ACTION_APPROVE, ACTION_REJECT}:
        return {"ok": False, "error": "Unknown agreement action."}
    config = load_config(app_path=Path(app_path))
    source = Path(app_path).read_text(encoding="utf-8")
    program_ir = lower_program(parse(source))
    if not program_ir.ais:
        raise Namel3ssError("No AI profile available for agreements.")
    team_id = resolve_team_id(project_root=str(Path(app_path).parent), app_path=app_path, config=config)
    proposal = None
    if proposal_id:
        proposal = session.memory_manager.agreements.get_pending(proposal_id)
    if proposal is None:
        proposal = session.memory_manager.agreements.select_pending(team_id, None)
    ai_profile = None
    if proposal and proposal.ai_profile:
        ai_profile = program_ir.ais.get(proposal.ai_profile)
    if ai_profile is None:
        ai_profile = next(iter(program_ir.ais.values()))
    identity = resolve_identity(config, getattr(program_ir, "identity", None))
    request = AgreementRequest(action=action, proposal_id=proposal_id, requested_by="studio")
    events = session.memory_manager.apply_agreement_action(
        ai_profile,
        session.state,
        request,
        identity=identity,
        project_root=str(Path(app_path).parent),
        app_path=app_path,
        team_id=team_id,
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
    proposals = session.memory_manager.list_team_proposals(team_id)
    trust_payload = {}
    policy = session.memory_manager.policy_for(ai_profile)
    contract = session.memory_manager.policy_contract_for(policy)
    actor_id = actor_id_from_identity(identity)
    actor_level = trust_level_from_identity(identity)
    trust_rules = contract.trust
    override_rules = rules_from_state(session.state, trust_rules)
    if override_rules is not None:
        decision = can_change_rules(actor_level, trust_rules)
        if decision.allowed:
            trust_rules = override_rules
    trust_payload = {
        "actor_id": actor_id,
        "actor_level": actor_level,
        "rules": trust_rules.as_dict(),
        "lines": trust_overview_lines(actor_id=actor_id, actor_level=actor_level, rules=trust_rules),
    }
    return {"ok": True, "team_id": team_id, "proposals": proposals, "traces": traces, "trust": trust_payload}


__all__ = ["apply_agreement_action_payload", "get_agreements_payload"]
