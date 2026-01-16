from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.agents.ids import agent_id_from_name, team_id_from_agent_ids
from namel3ss.ir.model.agents import (
    AgentDecl,
    AgentTeam,
    AgentTeamMember,
    ParallelAgentEntry,
    RunAgentStmt,
    RunAgentsParallelStmt,
)
from namel3ss.ir.model.ai import AIDecl


def _lower_agent_team(team: ast.AgentTeamDecl | None, agents: List[ast.AgentDecl]) -> AgentTeam | None:
    if team is None and not agents:
        return None
    members = list(team.members) if team is not None else [
        ast.AgentTeamMember(name=agent.name, role=None, line=agent.line, column=agent.column)
        for agent in agents
    ]
    if not members:
        raise Namel3ssError(
            build_guidance_message(
                what="Team of agents is empty.",
                why="A team of agents must list at least one agent.",
                fix="Add at least one agent name to the team.",
                example='team of agents\n  "planner"',
            ),
            line=getattr(team, "line", None),
            column=getattr(team, "column", None),
        )
    names = [member.name for member in members]
    duplicate = _first_duplicate_name(names)
    if duplicate:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Duplicate agent name '{duplicate}' in team of agents.",
                why="Agent names in a team must be unique.",
                fix="Remove the duplicate entry or rename one of the agents.",
                example='team of agents\n  "planner"\n  "reviewer"',
            ),
            line=_line_for_name(duplicate, members),
            column=_column_for_name(duplicate, members),
        )
    declared = {agent.name for agent in agents}
    if team is not None:
        missing = [name for name in names if name not in declared]
        if missing:
            missing_sorted = sorted(missing)
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Team of agents lists unknown agent '{missing_sorted[0]}'.",
                    why="Every team member must have a matching agent declaration.",
                    fix="Add the missing agent declaration or remove it from the team.",
                    example=f'agent "{missing_sorted[0]}":\n  ai is "assistant"',
                ),
                line=_line_for_name(missing_sorted[0], members),
                column=_column_for_name(missing_sorted[0], members),
            )
        extras = [name for name in sorted(declared) if name not in names]
        if extras:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Agent '{extras[0]}' is declared but not listed in the team.",
                    why="Teams must list every declared agent to define ordering and roles.",
                    fix="Add the agent to the team or remove the declaration.",
                    example=f'team of agents\n  "{extras[0]}"',
                ),
                line=_line_for_agent_name(extras[0], agents),
                column=_column_for_agent_name(extras[0], agents),
            )
    team_members: list[AgentTeamMember] = []
    id_owner: dict[str, str] = {}
    collisions: dict[str, set[str]] = {}
    for member in members:
        agent_id = agent_id_from_name(member.name)
        owner = id_owner.get(agent_id)
        if owner is None:
            id_owner[agent_id] = member.name
        elif owner != member.name:
            collisions.setdefault(agent_id, set()).update([owner, member.name])
        team_members.append(
            AgentTeamMember(
                name=member.name,
                agent_id=agent_id,
                role=member.role,
                line=member.line,
                column=member.column,
            )
        )
    if collisions:
        collision_id = sorted(collisions.keys())[0]
        offenders = sorted(collisions[collision_id])
        raise Namel3ssError(
            build_guidance_message(
                what=f"Agent id '{collision_id}' is assigned to multiple agents.",
                why="Agent ids must be unique after normalization.",
                fix="Rename one of the agents so their ids differ.",
                example=f'agent "{offenders[0]}":\n  ai is "assistant"',
            ),
            line=_line_for_name(offenders[0], members),
            column=_column_for_name(offenders[0], members),
        )
    team_id = team_id_from_agent_ids([member.agent_id for member in team_members])
    return AgentTeam(
        team_id=team_id,
        members=team_members,
        line=getattr(team, "line", None) if team is not None else getattr(agents[0], "line", None) if agents else None,
        column=getattr(team, "column", None) if team is not None else getattr(agents[0], "column", None) if agents else None,
    )


def _lower_agents(
    agents: List[ast.AgentDecl],
    ais: Dict[str, AIDecl],
    team: AgentTeam | None,
) -> Dict[str, AgentDecl]:
    agent_map: Dict[str, AgentDecl] = {}
    team_map = {member.name: member for member in team.members} if team is not None else {}
    for agent in agents:
        if agent.name in agent_map:
            raise Namel3ssError(f"Duplicate agent declaration '{agent.name}'", line=agent.line, column=agent.column)
        if agent.ai_name not in ais:
            raise Namel3ssError(f"Agent '{agent.name}' references unknown AI '{agent.ai_name}'", line=agent.line, column=agent.column)
        team_member = team_map.get(agent.name)
        agent_map[agent.name] = AgentDecl(
            name=agent.name,
            ai_name=agent.ai_name,
            system_prompt=agent.system_prompt,
            agent_id=team_member.agent_id if team_member else agent_id_from_name(agent.name),
            role=team_member.role if team_member else None,
            line=agent.line,
            column=agent.column,
        )
    return agent_map


def _validate_agent_reference(agent_name: str, agents: Dict[str, AgentDecl], line, column) -> None:
    if agent_name not in agents:
        raise Namel3ssError(f"Unknown agent '{agent_name}'", line=line, column=column)


def validate_agent_statement(stmt: RunAgentStmt | RunAgentsParallelStmt, agents: Dict[str, AgentDecl]) -> None:
    if isinstance(stmt, RunAgentStmt):
        _validate_agent_reference(stmt.agent_name, agents, stmt.line, stmt.column)
        return
    if isinstance(stmt, RunAgentsParallelStmt):
        if not stmt.entries:
            raise Namel3ssError("Parallel agent block requires at least one entry", line=stmt.line, column=stmt.column)
        for entry in stmt.entries:
            _validate_agent_reference(entry.agent_name, agents, entry.line, entry.column)
        return


def _first_duplicate_name(names: list[str]) -> str | None:
    seen: set[str] = set()
    for name in names:
        if name in seen:
            return name
        seen.add(name)
    return None


def _line_for_name(name: str, members: list[ast.AgentTeamMember]) -> int | None:
    for member in members:
        if member.name == name:
            return member.line
    return None


def _column_for_name(name: str, members: list[ast.AgentTeamMember]) -> int | None:
    for member in members:
        if member.name == name:
            return member.column
    return None


def _line_for_agent_name(name: str, agents: list[ast.AgentDecl]) -> int | None:
    for agent in agents:
        if agent.name == name:
            return agent.line
    return None


def _column_for_agent_name(name: str, agents: list[ast.AgentDecl]) -> int | None:
    for agent in agents:
        if agent.name == name:
            return agent.column
    return None
