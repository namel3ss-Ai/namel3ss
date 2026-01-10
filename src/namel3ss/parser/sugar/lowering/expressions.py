from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.sugar import grammar as sugar


def _lower_expression(expr: ast.Expression | None):
    if expr is None:
        return None
    if isinstance(expr, sugar.AccessExpr):
        current = _lower_expression(expr.base)
        for op in expr.ops:
            if isinstance(op, sugar.AccessIndex):
                current = ast.ListOpExpr(
                    kind="get",
                    target=current,
                    index=_lower_expression(op.index),
                    line=op.line,
                    column=op.column,
                )
            else:
                current = ast.MapOpExpr(
                    kind="get",
                    target=current,
                    key=ast.Literal(value=op.name, line=op.line, column=op.column),
                    line=op.line,
                    column=op.column,
                )
        return current
    if isinstance(expr, sugar.LatestRecordExpr):
        raise Namel3ssError(
            build_guidance_message(
                what="Latest record selector must be bound to a local name.",
                why="`latest` expands into record queries and cannot be nested inside other expressions.",
                fix='Bind it first: `let record is latest "MyRecord"` or `require latest "MyRecord" as record otherwise "..."`.',
                example='require latest "Order" as latest_order otherwise "Add an order first."',
            ),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.Literal):
        return expr
    if isinstance(expr, ast.VarReference):
        return expr
    if isinstance(expr, ast.AttrAccess):
        return expr
    if isinstance(expr, ast.StatePath):
        return expr
    if isinstance(expr, ast.UnaryOp):
        return ast.UnaryOp(op=expr.op, operand=_lower_expression(expr.operand), line=expr.line, column=expr.column)
    if isinstance(expr, ast.BinaryOp):
        return ast.BinaryOp(op=expr.op, left=_lower_expression(expr.left), right=_lower_expression(expr.right), line=expr.line, column=expr.column)
    if isinstance(expr, ast.Comparison):
        return ast.Comparison(kind=expr.kind, left=_lower_expression(expr.left), right=_lower_expression(expr.right), line=expr.line, column=expr.column)
    if isinstance(expr, ast.ToolCallExpr):
        args = [ast.ToolCallArg(name=arg.name, value=_lower_expression(arg.value), line=arg.line, column=arg.column) for arg in expr.arguments]
        return ast.ToolCallExpr(tool_name=expr.tool_name, arguments=args, line=expr.line, column=expr.column)
    if isinstance(expr, ast.ListExpr):
        return ast.ListExpr(items=[_lower_expression(item) for item in expr.items], line=expr.line, column=expr.column)
    if isinstance(expr, ast.MapExpr):
        entries = [
            ast.MapEntry(
                key=_lower_expression(entry.key),
                value=_lower_expression(entry.value),
                line=entry.line,
                column=entry.column,
            )
            for entry in expr.entries
        ]
        return ast.MapExpr(entries=entries, line=expr.line, column=expr.column)
    if isinstance(expr, ast.ListOpExpr):
        return ast.ListOpExpr(
            kind=expr.kind,
            target=_lower_expression(expr.target),
            value=_lower_expression(expr.value) if expr.value is not None else None,
            index=_lower_expression(expr.index) if expr.index is not None else None,
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.MapOpExpr):
        return ast.MapOpExpr(
            kind=expr.kind,
            target=_lower_expression(expr.target),
            key=_lower_expression(expr.key) if expr.key is not None else None,
            value=_lower_expression(expr.value) if expr.value is not None else None,
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.ListMapExpr):
        return ast.ListMapExpr(
            target=_lower_expression(expr.target),
            var_name=expr.var_name,
            body=_lower_expression(expr.body),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.ListFilterExpr):
        return ast.ListFilterExpr(
            target=_lower_expression(expr.target),
            var_name=expr.var_name,
            predicate=_lower_expression(expr.predicate),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.ListReduceExpr):
        return ast.ListReduceExpr(
            target=_lower_expression(expr.target),
            acc_name=expr.acc_name,
            item_name=expr.item_name,
            start=_lower_expression(expr.start),
            body=_lower_expression(expr.body),
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.CallFunctionExpr):
        args = [
            ast.FunctionCallArg(name=arg.name, value=_lower_expression(arg.value), line=arg.line, column=arg.column)
            for arg in expr.arguments
        ]
        return ast.CallFunctionExpr(function_name=expr.function_name, arguments=args, line=expr.line, column=expr.column)
    return expr
