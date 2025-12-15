from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.agents import AgentDecl
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
