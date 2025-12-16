from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Assignable, Expression


@dataclass
class Statement(Node):
    pass


@dataclass
class Let(Statement):
    name: str
    expression: Expression
    constant: bool = False


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
class AskAIStmt(Statement):
    ai_name: str
    input_expr: Expression
    target: str


@dataclass
class RunAgentStmt(Statement):
    agent_name: str
    input_expr: Expression
    target: str


@dataclass
class ParallelAgentEntry(Node):
    agent_name: str
    input_expr: Expression


@dataclass
class RunAgentsParallelStmt(Statement):
    entries: List[ParallelAgentEntry]
    target: str


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
    otherwise: Optional[List[Statement]]


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
