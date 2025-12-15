from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from namel3ss.ir.model.base import Node
from namel3ss.ir.model.statements import Statement
from namel3ss.ir.model.pages import Page
from namel3ss.ir.model.ai import AIDecl
from namel3ss.ir.model.agents import AgentDecl
from namel3ss.ir.model.tools import ToolDecl
from namel3ss.schema import records as schema


@dataclass
class Flow(Node):
    name: str
    body: List[Statement]


@dataclass
class Program(Node):
    records: List[schema.RecordSchema]
    flows: List[Flow]
    pages: List[Page]
    ais: Dict[str, AIDecl]
    tools: Dict[str, ToolDecl]
    agents: Dict[str, AgentDecl]
