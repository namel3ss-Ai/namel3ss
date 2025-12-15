from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ir.model.base import Node, Statement
from namel3ss.ir.model.expressions import Expression


@dataclass
class AgentDecl(Node):
    name: str
    ai_name: str
    system_prompt: Optional[str]


@dataclass
class ParallelAgentEntry(Node):
    agent_name: str
    input_expr: Expression


@dataclass
class RunAgentStmt(Statement):
    agent_name: str
    input_expr: Expression
    target: str


@dataclass
class RunAgentsParallelStmt(Statement):
    entries: List[ParallelAgentEntry]
    target: str
