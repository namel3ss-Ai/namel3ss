from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ast.base import Node


@dataclass
class AIFlowMetadata(Node):
    model: str
    prompt: str
    dataset: Optional[str] = None
    kind: Optional[str] = None
    output_type: Optional[str] = None
    labels: Optional[List[str]] = None
    sources: Optional[List[str]] = None


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


__all__ = ["AIFlowMetadata", "AIMemory", "AIDecl"]
