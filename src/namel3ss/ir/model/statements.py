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
class ParallelTask(Node):
    name: str
    body: List[Statement]


@dataclass
class ParallelMergePolicy(Node):
    policy: str


@dataclass
class ParallelBlock(Statement):
    tasks: List[ParallelTask]
    merge: ParallelMergePolicy | None = None


@dataclass
class OrchestrationBranch(Node):
    name: str
    call_expr: Expression


@dataclass
class OrchestrationMergePolicy(Node):
    policy: str
    precedence: List[str] | None = None


@dataclass
class OrchestrationBlock(Statement):
    branches: List[OrchestrationBranch]
    merge: OrchestrationMergePolicy
    target: str


@dataclass
class Repeat(Statement):
    count: Expression
    body: List[Statement]


@dataclass
class RepeatWhile(Statement):
    condition: Expression
    limit: int
    body: List[Statement]
    limit_line: int | None = None
    limit_column: int | None = None


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
class Create(Statement):
    record_name: str
    values: Expression
    target: str


@dataclass
class Find(Statement):
    record_name: str
    predicate: Expression


@dataclass
class UpdateField(Node):
    name: str
    expression: Expression


@dataclass
class Update(Statement):
    record_name: str
    predicate: Expression
    updates: List[UpdateField]


@dataclass
class Delete(Statement):
    record_name: str
    predicate: Expression


@dataclass
class ThemeChange(Statement):
    value: str


@dataclass
class EnqueueJob(Statement):
    job_name: str
    input_expr: Expression | None = None
    schedule_kind: str | None = None
    schedule_expr: Expression | None = None


@dataclass
class AdvanceTime(Statement):
    amount: Expression


@dataclass
class LogStmt(Statement):
    level: str
    message: Expression
    fields: Expression | None = None


@dataclass
class MetricStmt(Statement):
    kind: str
    name: str
    operation: str
    value: Expression | None = None
    labels: Expression | None = None
