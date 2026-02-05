from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Expression


@dataclass
class AIFlowDefinition(Node):
    name: str
    kind: str
    model: str
    prompt: str
    dataset: Optional[str] = None
    output_type: Optional[str] = None
    labels: Optional[list[str]] = None
    sources: Optional[list[str]] = None
    return_expr: Optional[Expression] = None


__all__ = ["AIFlowDefinition"]
