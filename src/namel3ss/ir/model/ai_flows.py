from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from namel3ss.ir.model.base import Node
from namel3ss.ir.model.expressions import Expression


@dataclass
class AIOutputField(Node):
    name: str
    type_name: str


@dataclass
class AIFlowTestConfig(Node):
    dataset: str
    metrics: list[str]


@dataclass
class ChainStep(Node):
    flow_kind: str | None
    flow_name: str
    input_expr: Expression


@dataclass
class AIFlowDefinition(Node):
    name: str
    kind: str
    model: Optional[str] = None
    prompt: Optional[str] = None
    prompt_expr: Optional[Expression] = None
    dataset: Optional[str] = None
    output_type: Optional[str] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    output_fields: Optional[list[AIOutputField]] = None
    labels: Optional[list[str]] = None
    sources: Optional[list[str]] = None
    chain_steps: Optional[list[ChainStep]] = None
    tests: Optional[AIFlowTestConfig] = None
    return_expr: Optional[Expression] = None


__all__ = ["AIFlowDefinition", "AIFlowTestConfig", "AIOutputField", "ChainStep"]
