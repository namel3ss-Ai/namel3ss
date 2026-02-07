from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, TYPE_CHECKING

from namel3ss.ir.model.base import Node
from namel3ss.ir.model.statements import Statement
from namel3ss.ir.model.pages import Page
from namel3ss.ir.model.expressions import Expression
from namel3ss.ir.model.ai import AIDecl, AIFlowMetadata
from namel3ss.ir.model.agents import AgentDecl, AgentTeam
from namel3ss.ir.model.jobs import JobDecl
from namel3ss.ir.model.policy import PolicyDecl
from namel3ss.ir.model.contracts import ContractDecl
from namel3ss.ir.model.tools import ToolDecl
from namel3ss.ir.model.routes import RouteDefinition
from namel3ss.ir.model.prompts import PromptDefinition
from namel3ss.ir.model.crud import CrudDefinition
from namel3ss.ir.model.ai_flows import AIFlowDefinition
from namel3ss.ir.functions.model import FunctionDecl
from namel3ss.schema import records as schema
if TYPE_CHECKING:  # pragma: no cover - typing-only
    from namel3ss.schema.identity import IdentitySchema
    from namel3ss.ir.model.flow_steps import FlowStep


@dataclass
class Flow(Node):
    name: str
    body: List[Statement]
    requires: Expression | None = None
    audited: bool = False
    purity: str = "effectful"
    steps: List["FlowStep"] | None = None
    declarative: bool = False
    ai_metadata: AIFlowMetadata | None = None


@dataclass
class Program(Node):
    spec_version: str
    theme: str
    theme_tokens: Dict[str, str]
    theme_runtime_supported: bool
    theme_preference: Dict[str, object]
    ui_settings: Dict[str, str]
    capabilities: tuple[str, ...]
    records: List[schema.RecordSchema]
    functions: Dict[str, FunctionDecl]
    flow_contracts: Dict[str, ContractDecl]
    flows: List[Flow]
    routes: List[RouteDefinition]
    crud: List[CrudDefinition]
    prompts: List[PromptDefinition]
    ai_flows: List[AIFlowDefinition]
    jobs: List[JobDecl]
    pages: List[Page]
    ais: Dict[str, AIDecl]
    tools: Dict[str, ToolDecl]
    agents: Dict[str, AgentDecl]
    policy: PolicyDecl | None = None
    agent_team: AgentTeam | None = None
    identity: "IdentitySchema | None" = None
    state_defaults: dict | None = None
    ui_active_page_rules: list["ActivePageRule"] | None = None
    ui_plugins: tuple[str, ...] = tuple()
