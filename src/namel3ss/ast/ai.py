from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ast.base import Node


@dataclass
class AIMemory(Node):
    short_term: int = 0
    semantic: bool = False
    profile: bool = False


@dataclass
class AIDecl(Node):
    name: str
    model: str
    provider: str | None
    system_prompt: Optional[str]
    exposed_tools: List[str]
    memory: AIMemory
