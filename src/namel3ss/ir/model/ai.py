from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ir.model.base import Node, Statement
from namel3ss.ir.model.expressions import Expression


@dataclass
class AIMemory(Node):
    short_term: int = 0
    semantic: bool = False
    profile: bool = False


@dataclass
class AIDecl(Node):
    name: str
    model: str
    provider: str
    system_prompt: Optional[str]
    exposed_tools: List[str]
    memory: AIMemory


@dataclass
class AskAIStmt(Statement):
    ai_name: str
    input_expr: Expression
    target: str
