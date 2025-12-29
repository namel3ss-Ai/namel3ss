from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from namel3ss.ast.base import Node


@dataclass
class UseDecl(Node):
    module: str
    alias: str
    module_path: str | None = None
    only: List[str] = field(default_factory=list)
    allow_override: List[str] = field(default_factory=list)


@dataclass
class CapsuleExport(Node):
    kind: str
    name: str


@dataclass
class CapsuleDecl(Node):
    name: str
    exports: List[CapsuleExport]
