from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from namel3ss.ast.base import Node
from namel3ss.ast.modules import CapsuleDecl, UseDecl
from namel3ss.ast.expressions import Expression
from namel3ss.ast.identity import IdentityDecl
from namel3ss.ast.ui_packs import UIPackDecl


@dataclass
class Flow(Node):
    name: str
    body: List["Statement"]
    requires: Optional[Expression] = None
    audited: bool = False


@dataclass
class Program(Node):
    spec_version: str | None
    app_theme: str
    app_theme_line: int | None
    app_theme_column: int | None
    theme_tokens: Dict[str, tuple[str, int | None, int | None]]
    theme_preference: Dict[str, tuple[object, int | None, int | None]]
    records: List["RecordDecl"]
    functions: List["FunctionDecl"]
    flows: List[Flow]
    pages: List["PageDecl"]
    ais: List["AIDecl"]
    tools: List["ToolDecl"]
    agents: List["AgentDecl"]
    ui_packs: List[UIPackDecl]
    uses: List[UseDecl]
    capsule: Optional[CapsuleDecl]
    identity: Optional[IdentityDecl] = None
    state_defaults: dict | None = None
