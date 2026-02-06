from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ir.model.ai_flows import AIFlowTestConfig, AIOutputField, ChainStep
from namel3ss.ir.model.base import Node, Statement
from namel3ss.ir.model.expressions import Expression


@dataclass
class AIMemory(Node):
    short_term: int = 0
    semantic: bool = False
    profile: bool = False


@dataclass
class AIFlowMetadata(Node):
    model: str | None
    prompt: str | None
    prompt_expr: Expression | None = None
    dataset: Optional[str] = None
    kind: Optional[str] = None
    output_type: Optional[str] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    output_fields: Optional[list[AIOutputField]] = None
    labels: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    chain_steps: Optional[list[ChainStep]] = None
    tests: Optional[AIFlowTestConfig] = None


@dataclass
class AIDecl(Node):
    name: str
    model: str
    provider: str
    system_prompt: Optional[str]
    exposed_tools: List[str]
    memory: AIMemory


@dataclass
class AskAIStmt(Statement):
    ai_name: str
    input_expr: Expression
    target: str
    input_mode: str = "text"
    stream: bool = False


__all__ = ["AIFlowMetadata", "AIMemory", "AIDecl", "AskAIStmt"]
