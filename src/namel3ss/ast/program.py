from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, TYPE_CHECKING

from namel3ss.ast.base import Node
from namel3ss.ast.jobs import JobDecl
from namel3ss.ast.modules import CapsuleDecl, UseDecl
from namel3ss.ast.expressions import Expression
from namel3ss.ast.identity import IdentityDecl
from namel3ss.ast.policy import PolicyDecl
from namel3ss.ast.ui_packs import UIPackDecl
if TYPE_CHECKING:  # pragma: no cover - typing-only
    from namel3ss.ast.flow_steps import FlowStep


@dataclass
class Flow(Node):
    name: str
    body: List["Statement"]
    requires: Optional[Expression] = None
    audited: bool = False
    steps: List["FlowStep"] | None = None
    declarative: bool = False


@dataclass
class Program(Node):
    spec_version: str | None
    app_theme: str
    app_theme_line: int | None
    app_theme_column: int | None
    theme_tokens: Dict[str, tuple[str, int | None, int | None]]
    theme_preference: Dict[str, tuple[object, int | None, int | None]]
    ui_settings: Dict[str, tuple[str, int | None, int | None]]
    ui_line: int | None
    ui_column: int | None
    capabilities: List[str]
    records: List["RecordDecl"]
    functions: List["FunctionDecl"]
    flows: List[Flow]
    jobs: List[JobDecl]
    pages: List["PageDecl"]
    ais: List["AIDecl"]
    tools: List["ToolDecl"]
    agents: List["AgentDecl"]
    ui_packs: List[UIPackDecl]
    uses: List[UseDecl]
    capsule: Optional[CapsuleDecl]
    policy: PolicyDecl | None = None
    agent_team: "AgentTeamDecl | None" = None
    identity: Optional[IdentityDecl] = None
    state_defaults: dict | None = None
