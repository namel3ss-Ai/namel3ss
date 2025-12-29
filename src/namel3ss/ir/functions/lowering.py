from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.functions.model import FunctionDecl, FunctionParam, FunctionSignature
from namel3ss.ir.functions.validate import validate_functions
from namel3ss.ir.lowering.statements import _lower_statement


def lower_functions(functions: List[ast.FunctionDecl], agents) -> Dict[str, FunctionDecl]:
    function_map: Dict[str, FunctionDecl] = {}
    for func in functions:
        if func.name in function_map:
            raise Namel3ssError(
                f"Duplicate function declaration '{func.name}'",
                line=func.line,
                column=func.column,
            )
        inputs = [
            FunctionParam(
                name=param.name,
                type_name=param.type_name,
                required=param.required,
                line=param.line,
                column=param.column,
            )
            for param in func.signature.inputs
        ]
        outputs = None
        if func.signature.outputs is not None:
            outputs = [
                FunctionParam(
                    name=param.name,
                    type_name=param.type_name,
                    required=param.required,
                    line=param.line,
                    column=param.column,
                )
                for param in func.signature.outputs
            ]
        signature = FunctionSignature(inputs=inputs, outputs=outputs, line=func.signature.line, column=func.signature.column)
        body = [_lower_statement(stmt, agents) for stmt in func.body]
        function_map[func.name] = FunctionDecl(
            name=func.name,
            signature=signature,
            body=body,
            line=func.line,
            column=func.column,
        )
    validate_functions(function_map)
    return function_map


__all__ = ["lower_functions"]
