from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, TYPE_CHECKING

from namel3ss.ir.model.base import Node
from namel3ss.ir.model.statements import Statement
from namel3ss.ir.model.pages import Page
from namel3ss.ir.model.expressions import Expression
from namel3ss.ir.model.ai import AIDecl
from namel3ss.ir.model.agents import AgentDecl
from namel3ss.ir.model.tools import ToolDecl
from namel3ss.ir.functions.model import FunctionDecl
from namel3ss.schema import records as schema
if TYPE_CHECKING:  # pragma: no cover - typing-only
    from namel3ss.schema.identity import IdentitySchema


@dataclass
class Flow(Node):
    name: str
    body: List[Statement]
    requires: Expression | None = None
    audited: bool = False


@dataclass
class Program(Node):
    spec_version: str
    theme: str
    theme_tokens: Dict[str, str]
    theme_runtime_supported: bool
    theme_preference: Dict[str, object]
    records: List[schema.RecordSchema]
    functions: Dict[str, FunctionDecl]
    flows: List[Flow]
    pages: List[Page]
    ais: Dict[str, AIDecl]
    tools: Dict[str, ToolDecl]
    agents: Dict[str, AgentDecl]
    identity: "IdentitySchema | None" = None
    state_defaults: dict | None = None
