from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

from namel3ss.ast.base import Node
from namel3ss.ast.jobs import JobDecl
from namel3ss.ast.modules import CapsuleDecl, PluginUseDecl, UseDecl
from namel3ss.ast.expressions import Expression
from namel3ss.ast.identity import IdentityDecl
from namel3ss.ast.policy import PolicyDecl
from namel3ss.ast.ui_packs import UIPackDecl
from namel3ss.ast.ui_patterns import UIPatternDecl
from namel3ss.ast.ai import AIFlowMetadata
from namel3ss.ast.routes import RouteDefinition
from namel3ss.ast.crud import CrudDefinition
from namel3ss.ast.prompts import PromptDefinition
from namel3ss.ast.ai_flows import AIFlowDefinition
if TYPE_CHECKING:  # pragma: no cover - typing-only
    from namel3ss.ast.flow_steps import FlowStep
    from namel3ss.ast.contracts import ContractDecl


@dataclass
class Flow(Node):
    name: str
    body: List["Statement"]
    requires: Optional[Expression] = None
    audited: bool = False
    purity: str = "effectful"
    steps: List["FlowStep"] | None = None
    declarative: bool = False
    ai_metadata: AIFlowMetadata | None = None


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
    contracts: List["ContractDecl"]
    flows: List[Flow]
    routes: List[RouteDefinition]
    crud: List[CrudDefinition]
    prompts: List[PromptDefinition]
    ai_flows: List[AIFlowDefinition]
    jobs: List[JobDecl]
    pages: List["PageDecl"]
    ais: List["AIDecl"]
    tools: List["ToolDecl"]
    agents: List["AgentDecl"]
    ui_packs: List[UIPackDecl]
    ui_patterns: List[UIPatternDecl]
    uses: List[UseDecl]
    capsule: Optional[CapsuleDecl]
    ui_active_page_rules: list["ActivePageRule"] | None = None
    policy: PolicyDecl | None = None
    agent_team: "AgentTeamDecl | None" = None
    identity: Optional[IdentityDecl] = None
    state_defaults: dict | None = None
    plugin_uses: List[PluginUseDecl] = field(default_factory=list)
