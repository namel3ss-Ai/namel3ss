from __future__ import annotations

from dataclasses import dataclass
from typing import List, Union

from namel3ss.ir.model.base import Expression


@dataclass
class Literal(Expression):
    value: Union[str, int, bool]


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


Assignable = Union[VarReference, StatePath]
