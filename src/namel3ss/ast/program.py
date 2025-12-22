from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

from namel3ss.ast.base import Node


@dataclass
class Flow(Node):
    name: str
    body: List["Statement"]


@dataclass
class Program(Node):
    app_theme: str
    app_theme_line: int | None
    app_theme_column: int | None
    theme_tokens: Dict[str, tuple[str, int | None, int | None]]
    theme_preference: Dict[str, tuple[object, int | None, int | None]]
    records: List["RecordDecl"]
    flows: List[Flow]
    pages: List["PageDecl"]
    ais: List["AIDecl"]
    tools: List["ToolDecl"]
    agents: List["AgentDecl"]
