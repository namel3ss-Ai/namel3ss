from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Expression


@dataclass
class CallArg(Node):
    name: str
    value: Expression


@dataclass
class CallFlowExpr(Expression):
    flow_name: str
    arguments: List[CallArg]
    outputs: List[str]


@dataclass
class CallPipelineExpr(Expression):
    pipeline_name: str
    arguments: List[CallArg]
    outputs: List[str]


__all__ = ["CallArg", "CallFlowExpr", "CallPipelineExpr"]
