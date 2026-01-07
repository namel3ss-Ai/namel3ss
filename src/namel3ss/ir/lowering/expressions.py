from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.model.expressions import (
    Assignable,
    AttrAccess,
    BinaryOp,
    Comparison,
    ListExpr,
    ListFilterExpr,
    ListMapExpr,
    ListReduceExpr,
    Literal,
    MapEntry,
    MapExpr,
    ListOpExpr,
    MapOpExpr,
    StatePath,
    ToolCallArg,
    ToolCallExpr,
    UnaryOp,
    VarReference,
)
from namel3ss.ir.functions.model import CallFunctionExpr, FunctionCallArg


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
    if isinstance(expr, ast.ListExpr):
        return ListExpr(
            items=[_lower_expression(item) for item in expr.items],
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.MapExpr):
        entries = [
            MapEntry(
                key=_lower_expression(entry.key),
                value=_lower_expression(entry.value),
                line=entry.line,
                column=entry.column,
            )
            for entry in expr.entries
        ]
        return MapExpr(entries=entries, line=expr.line, column=expr.column)
    if isinstance(expr, ast.ListOpExpr):
        return ListOpExpr(
            kind=expr.kind,
            target=_lower_expression(expr.target),
            value=_lower_expression(expr.value) if expr.value is not None else None,
            index=_lower_expression(expr.index) if expr.index is not None else None,
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.ListMapExpr):
        return ListMapExpr(
            target=_lower_expression(expr.target),
            var_name=expr.var_name,
            body=_lower_expression(expr.body),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.ListFilterExpr):
        return ListFilterExpr(
            target=_lower_expression(expr.target),
            var_name=expr.var_name,
            predicate=_lower_expression(expr.predicate),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.ListReduceExpr):
        return ListReduceExpr(
            target=_lower_expression(expr.target),
            acc_name=expr.acc_name,
            item_name=expr.item_name,
            start=_lower_expression(expr.start),
            body=_lower_expression(expr.body),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.MapOpExpr):
        return MapOpExpr(
            kind=expr.kind,
            target=_lower_expression(expr.target),
            key=_lower_expression(expr.key) if expr.key is not None else None,
            value=_lower_expression(expr.value) if expr.value is not None else None,
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.CallFunctionExpr):
        args = [
            FunctionCallArg(name=arg.name, value=_lower_expression(arg.value), line=arg.line, column=arg.column)
            for arg in expr.arguments
        ]
        return CallFunctionExpr(
            function_name=expr.function_name,
            arguments=args,
            line=expr.line,
            column=expr.column,
        )
    raise TypeError(f"Unhandled expression type: {type(expr)}")
