from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.model.expressions import (
    Assignable,
    AttrAccess,
    BinaryOp,
    Comparison,
    Literal,
    StatePath,
    ToolCallArg,
    ToolCallExpr,
    UnaryOp,
    VarReference,
)


def _lower_assignable(expr: ast.Assignable) -> Assignable:
    if isinstance(expr, ast.VarReference):
        return VarReference(name=expr.name, line=expr.line, column=expr.column)
    if isinstance(expr, ast.StatePath):
        return StatePath(path=list(expr.path), line=expr.line, column=expr.column)
    raise TypeError(f"Unhandled assignable type: {type(expr)}")


def _lower_expression(expr: ast.Expression | None):
    if expr is None:
        return None
    if isinstance(expr, ast.Literal):
        return Literal(value=expr.value, line=expr.line, column=expr.column)
    if isinstance(expr, ast.VarReference):
        return VarReference(name=expr.name, line=expr.line, column=expr.column)
    if isinstance(expr, ast.AttrAccess):
        return AttrAccess(base=expr.base, attrs=list(expr.attrs), line=expr.line, column=expr.column)
    if isinstance(expr, ast.StatePath):
        return StatePath(path=list(expr.path), line=expr.line, column=expr.column)
    if isinstance(expr, ast.UnaryOp):
        return UnaryOp(
            op=expr.op,
            operand=_lower_expression(expr.operand),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.BinaryOp):
        return BinaryOp(
            op=expr.op,
            left=_lower_expression(expr.left),
            right=_lower_expression(expr.right),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.Comparison):
        return Comparison(
            kind=expr.kind,
            left=_lower_expression(expr.left),
            right=_lower_expression(expr.right),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.ToolCallExpr):
        args = [
            ToolCallArg(name=arg.name, value=_lower_expression(arg.value), line=arg.line, column=arg.column)
            for arg in expr.arguments
        ]
        return ToolCallExpr(
            tool_name=expr.tool_name,
            arguments=args,
            line=expr.line,
            column=expr.column,
        )
    raise TypeError(f"Unhandled expression type: {type(expr)}")
