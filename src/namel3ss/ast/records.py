from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Expression


@dataclass
class FieldConstraint(Node):
    kind: str  # present, unique, gt, gte, lt, lte, between, int, pattern, len_min, len_max
    expression: Optional[Expression] = None
    expression_high: Optional[Expression] = None
    pattern: Optional[str] = None


@dataclass
class FieldDecl(Node):
    name: str
    type_name: str
    constraint: Optional[FieldConstraint]
    type_was_alias: bool = False
    raw_type_name: Optional[str] = None
    type_line: Optional[int] = None
    type_column: Optional[int] = None


@dataclass
class RecordDecl(Node):
    name: str
    fields: List[FieldDecl]
    tenant_key: Optional[Expression] = None
    ttl_hours: Optional[Expression] = None
