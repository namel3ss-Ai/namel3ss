from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ir.model.base import Node


@dataclass
class ToolDecl(Node):
    name: str
    kind: str
