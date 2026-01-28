from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ir.functions.model import FunctionSignature
from namel3ss.ir.model.base import Node


@dataclass
class ContractDecl(Node):
    kind: str
    name: str
    signature: FunctionSignature


__all__ = ["ContractDecl"]
