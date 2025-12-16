from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from namel3ss.ast.base import Node


@dataclass
class AgentDecl(Node):
    name: str
    ai_name: str
    system_prompt: Optional[str]
