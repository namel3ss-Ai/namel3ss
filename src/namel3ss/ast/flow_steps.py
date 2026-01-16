from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast.base import Node
from namel3ss.ast.expressions import Expression


@dataclass
class FlowStep(Node):
    pass


@dataclass
class FlowInputField(Node):
    name: str
    type_name: str
    type_was_alias: bool = False
    raw_type_name: str | None = None
    type_line: int | None = None
    type_column: int | None = None


@dataclass
class FlowInput(FlowStep):
    fields: list[FlowInputField]


@dataclass
class FlowRequire(FlowStep):
    condition: str


@dataclass
class FlowField(Node):
    name: str
    value: Expression


@dataclass
class FlowCreate(FlowStep):
    record_name: str
    fields: list[FlowField]


@dataclass
class FlowUpdate(FlowStep):
    record_name: str
    selector: str | None
    updates: list[FlowField]


@dataclass
class FlowDelete(FlowStep):
    record_name: str
    selector: str | None


@dataclass
class FlowCallForeign(FlowStep):
    foreign_name: str
    arguments: list[FlowField]


__all__ = [
    "FlowCallForeign",
    "FlowCreate",
    "FlowDelete",
    "FlowField",
    "FlowInput",
    "FlowInputField",
    "FlowRequire",
    "FlowStep",
    "FlowUpdate",
]
