from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Union

from namel3ss.ir.model.base import Expression, Node


@dataclass
class Literal(Expression):
    value: Union[str, int, bool, Decimal]


@dataclass
class VarReference(Expression):
    name: str


@dataclass
class AttrAccess(Expression):
    base: str
    attrs: List[str]


@dataclass
class StatePath(Expression):
    path: List[str]


@dataclass
class UnaryOp(Expression):
    op: str
    operand: Expression


@dataclass
class BinaryOp(Expression):
    op: str
    left: Expression
    right: Expression


@dataclass
class Comparison(Expression):
    kind: str
    left: Expression
    right: Expression


@dataclass
class ToolCallExpr(Expression):
    tool_name: str
    arguments: List["ToolCallArg"]


@dataclass
class ToolCallArg(Node):
    name: str
    value: Expression


@dataclass
class ListExpr(Expression):
    items: List[Expression]


@dataclass
class MapEntry(Node):
    key: Expression
    value: Expression


@dataclass
class MapExpr(Expression):
    entries: List[MapEntry]


@dataclass
class ListOpExpr(Expression):
    kind: str
    target: Expression
    value: Expression | None = None
    index: Expression | None = None


@dataclass
class ListMapExpr(Expression):
    target: Expression
    var_name: str
    body: Expression


@dataclass
class ListFilterExpr(Expression):
    target: Expression
    var_name: str
    predicate: Expression


@dataclass
class ListReduceExpr(Expression):
    target: Expression
    acc_name: str
    item_name: str
    start: Expression
    body: Expression


@dataclass
class MapOpExpr(Expression):
    kind: str
    target: Expression
    key: Expression | None = None
    value: Expression | None = None


Assignable = Union[VarReference, StatePath]
