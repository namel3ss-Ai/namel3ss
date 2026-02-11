from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast.base import Node


@dataclass
class IncludeDecl(Node):
    path_raw: str
    path_norm: str


__all__ = ["IncludeDecl"]
