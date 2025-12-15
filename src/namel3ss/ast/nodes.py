from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class Node:
    line: Optional[int]
    column: Optional[int]


@dataclass
class Flow(Node):
    name: str
    body: List["Statement"]


@dataclass
class Program(Node):
    records: List["RecordDecl"]
    flows: List[Flow]
    pages: List["PageDecl"]
    ais: List["AIDecl"]
    tools: List["ToolDecl"]
    agents: List["AgentDecl"]


@dataclass
class Statement(Node):
    pass


@dataclass
class Let(Statement):
    name: str
    expression: "Expression"
    constant: bool = False


@dataclass
class Set(Statement):
    target: "Assignable"
    expression: "Expression"


@dataclass
class If(Statement):
    condition: "Expression"
    then_body: List[Statement]
    else_body: List[Statement]


@dataclass
class Return(Statement):
    expression: "Expression"


@dataclass
class AskAIStmt(Statement):
    ai_name: str
    input_expr: "Expression"
    target: str


@dataclass
class RunAgentStmt(Statement):
    agent_name: str
    input_expr: "Expression"
    target: str


@dataclass
class ParallelAgentEntry(Node):
    agent_name: str
    input_expr: "Expression"


@dataclass
class RunAgentsParallelStmt(Statement):
    entries: List[ParallelAgentEntry]
    target: str


@dataclass
class Repeat(Statement):
    count: "Expression"
    body: List[Statement]


@dataclass
class ForEach(Statement):
    name: str
    iterable: "Expression"
    body: List[Statement]


@dataclass
class MatchCase(Node):
    pattern: "Expression"
    body: List[Statement]


@dataclass
class Match(Statement):
    expression: "Expression"
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
    predicate: "Expression"


@dataclass
class Expression(Node):
    pass


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
    kind: str  # eq, gt, lt
    left: Expression
    right: Expression


Assignable = Union[VarReference, StatePath]




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


@dataclass
class PageItem(Node):
    pass


@dataclass
class TitleItem(PageItem):
    value: str


@dataclass
class TextItem(PageItem):
    value: str


@dataclass
class FormItem(PageItem):
    record_name: str


@dataclass
class TableItem(PageItem):
    record_name: str


@dataclass
class ButtonItem(PageItem):
    label: str
    flow_name: str


@dataclass
class PageDecl(Node):
    name: str
    items: List[PageItem]


@dataclass
class AIDecl(Node):
    name: str
    model: str
    system_prompt: Optional[str]
    exposed_tools: List[str]
    memory: "AIMemory"


@dataclass
class ToolDecl(Node):
    name: str
    kind: str


@dataclass
class AgentDecl(Node):
    name: str
    ai_name: str
    system_prompt: Optional[str]


@dataclass
class AIMemory(Node):
    short_term: int = 0
    semantic: bool = False
    profile: bool = False
