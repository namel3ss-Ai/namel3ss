from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast.base import Node


@dataclass
class Flow(Node):
    name: str
    body: List["Statement"]


@dataclass
class Program(Node):
    records: List["RecordDecl"]
    flows: List[Flow]
    pages: List["PageDecl"]
    ais: List["AIDecl"]
    tools: List["ToolDecl"]
    agents: List["AgentDecl"]
