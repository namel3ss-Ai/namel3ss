from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.agents import AgentDecl, ParallelAgentEntry, RunAgentStmt, RunAgentsParallelStmt
from namel3ss.ir.model.ai import AIDecl


def _lower_agents(agents: List[ast.AgentDecl], ais: Dict[str, AIDecl]) -> Dict[str, AgentDecl]:
    agent_map: Dict[str, AgentDecl] = {}
    for agent in agents:
        if agent.name in agent_map:
            raise Namel3ssError(f"Duplicate agent declaration '{agent.name}'", line=agent.line, column=agent.column)
        if agent.ai_name not in ais:
            raise Namel3ssError(f"Agent '{agent.name}' references unknown AI '{agent.ai_name}'", line=agent.line, column=agent.column)
        agent_map[agent.name] = AgentDecl(
            name=agent.name,
            ai_name=agent.ai_name,
            system_prompt=agent.system_prompt,
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
