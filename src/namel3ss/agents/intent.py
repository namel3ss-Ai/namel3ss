from __future__ import annotations

from typing import Iterable

from namel3ss.agents.ids import agent_id_from_name, team_id_from_agent_ids
from namel3ss.ir import nodes as ir


def build_agent_team_intent(program: ir.Program) -> dict | None:
    team = getattr(program, "agent_team", None)
    if team is not None and getattr(team, "members", None):
        members = [
            _member_payload(member.name, member.agent_id, member.role)
            for member in team.members
        ]
        return {"team_id": team.team_id, "agents": members}
    agents_map = getattr(program, "agents", {}) or {}
    if not agents_map:
        return None
    ordered = ordered_agent_decls(program)
    members = [
        _member_payload(
            agent.name,
            agent.agent_id or agent_id_from_name(agent.name),
            agent.role,
        )
        for agent in ordered
    ]
    return {"team_id": team_id_from_agent_ids(_agent_ids(members)), "agents": members}


def ordered_agent_decls(program: ir.Program) -> list[ir.AgentDecl]:
    agents_map = getattr(program, "agents", {}) or {}
    team = getattr(program, "agent_team", None)
    if team is None or not getattr(team, "members", None):
        return [agents_map[name] for name in sorted(agents_map.keys())]
    ordered: list[ir.AgentDecl] = []
    seen: set[str] = set()
    for member in team.members:
        agent = agents_map.get(member.name)
        if agent is None:
            continue
        ordered.append(agent)
        seen.add(member.name)
    leftovers = [agents_map[name] for name in sorted(agents_map.keys()) if name not in seen]
    ordered.extend(leftovers)
    return ordered


def _member_payload(name: str, agent_id: str, role: str | None) -> dict:
    payload = {"name": name, "agent_id": agent_id}
    if role:
        payload["role"] = role
    return payload


def _agent_ids(members: Iterable[dict]) -> list[str]:
    return [str(member.get("agent_id") or "") for member in members]


__all__ = ["build_agent_team_intent", "ordered_agent_decls"]
