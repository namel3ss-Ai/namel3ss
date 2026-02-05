from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast.base import Node


@dataclass
class CrudDefinition(Node):
    record_name: str


__all__ = ["CrudDefinition"]
