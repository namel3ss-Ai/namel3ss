from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ir.model.base import Node


@dataclass
class CrudDefinition(Node):
    record_name: str


__all__ = ["CrudDefinition"]
