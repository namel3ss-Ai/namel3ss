from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ir.model.base import Expression, Node


@dataclass
class FunctionParam(Node):
    name: str
    type_name: str
    required: bool = True


@dataclass
class FunctionSignature(Node):
    inputs: List[FunctionParam]
    outputs: Optional[List[FunctionParam]] = None


@dataclass
class FunctionDecl(Node):
    name: str
    signature: FunctionSignature
    body: List["Statement"]


@dataclass
class FunctionCallArg(Node):
    name: str
    value: Expression


@dataclass
class CallFunctionExpr(Expression):
    function_name: str
    arguments: List[FunctionCallArg]


__all__ = [
    "CallFunctionExpr",
    "FunctionCallArg",
    "FunctionDecl",
    "FunctionParam",
    "FunctionSignature",
]
