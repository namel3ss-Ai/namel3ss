from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Expression


@dataclass
class FieldConstraint(Node):
    kind: str  # present, unique, gt, lt, pattern, len_min, len_max
    expression: Optional[Expression] = None
    pattern: Optional[str] = None


@dataclass
class FieldDecl(Node):
    name: str
    type_name: str
    constraint: Optional[FieldConstraint]


@dataclass
class RecordDecl(Node):
    name: str
    fields: List[FieldDecl]
