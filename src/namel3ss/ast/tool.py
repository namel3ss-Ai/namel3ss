from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast.base import Node


@dataclass
class ToolField(Node):
    name: str
    type_name: str
    required: bool = True


@dataclass
class ToolDecl(Node):
    name: str
    kind: str
    input_fields: list[ToolField]
    output_fields: list[ToolField]
    capabilities: tuple[str, ...] = ()
    purity: str = "impure"
    timeout_seconds: int | None = None
