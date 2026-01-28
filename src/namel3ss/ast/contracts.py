from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast.base import Node
from namel3ss.ast.functions import FunctionSignature


@dataclass
class ContractDecl(Node):
    kind: str
    name: str
    signature: FunctionSignature


__all__ = ["ContractDecl"]
