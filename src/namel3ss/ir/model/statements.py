from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ir.model.base import Node, Statement
from namel3ss.ir.model.expressions import Assignable, Expression


@dataclass
class Let(Statement):
    name: str
    expression: Expression
    constant: bool


@dataclass
class Set(Statement):
    target: Assignable
    expression: Expression


@dataclass
class If(Statement):
    condition: Expression
    then_body: List[Statement]
    else_body: List[Statement]


@dataclass
class Return(Statement):
    expression: Expression


@dataclass
class Repeat(Statement):
    count: Expression
    body: List[Statement]


@dataclass
class ForEach(Statement):
    name: str
    iterable: Expression
    body: List[Statement]


@dataclass
class MatchCase(Node):
    pattern: Expression
    body: List[Statement]


@dataclass
class Match(Statement):
    expression: Expression
    cases: List[MatchCase]
    otherwise: List[Statement] | None


@dataclass
class TryCatch(Statement):
    try_body: List[Statement]
    catch_var: str
    catch_body: List[Statement]


@dataclass
class Save(Statement):
    record_name: str


@dataclass
class Find(Statement):
    record_name: str
    predicate: Expression
