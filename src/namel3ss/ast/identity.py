from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast.base import Node
from namel3ss.ast.records import FieldDecl


@dataclass
class IdentityDecl(Node):
    name: str
    fields: List[FieldDecl]
    trust_levels: List[str] | None
