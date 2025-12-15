from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.context import ExecutionContext


def evaluate_expression(ctx: ExecutionContext, expr: ir.Expression) -> object:
    if isinstance(expr, ir.Literal):
        return expr.value
    if isinstance(expr, ir.VarReference):
        if expr.name not in ctx.locals:
            raise Namel3ssError(
                f"Unknown variable '{expr.name}'",
                line=expr.line,
                column=expr.column,
            )
        return ctx.locals[expr.name]
    if isinstance(expr, ir.AttrAccess):
        if expr.base not in ctx.locals:
            raise Namel3ssError(
                f"Unknown variable '{expr.base}'",
                line=expr.line,
                column=expr.column,
            )
        value = ctx.locals[expr.base]
        for attr in expr.attrs:
            if isinstance(value, dict):
                if attr not in value:
                    raise Namel3ssError(
                        f"Missing attribute '{attr}'",
                        line=expr.line,
                        column=expr.column,
                    )
                value = value[attr]
                continue
            if not hasattr(value, attr):
                raise Namel3ssError(
                    f"Missing attribute '{attr}'",
                    line=expr.line,
                    column=expr.column,
                )
            value = getattr(value, attr)
        return value
    if isinstance(expr, ir.StatePath):
        return resolve_state_path(ctx, expr)
    if isinstance(expr, ir.UnaryOp):
        operand = evaluate_expression(ctx, expr.operand)
        if expr.op == "not":
            if not isinstance(operand, bool):
                raise Namel3ssError("Operand to 'not' must be boolean", line=expr.line, column=expr.column)
            return not operand
        raise Namel3ssError(f"Unsupported unary op '{expr.op}'", line=expr.line, column=expr.column)
    if isinstance(expr, ir.BinaryOp):
        if expr.op == "and":
            left = evaluate_expression(ctx, expr.left)
            if not isinstance(left, bool):
                raise Namel3ssError("Left operand of 'and' must be boolean", line=expr.line, column=expr.column)
            if not left:
                return False
            right = evaluate_expression(ctx, expr.right)
            if not isinstance(right, bool):
                raise Namel3ssError("Right operand of 'and' must be boolean", line=expr.line, column=expr.column)
            return left and right
        if expr.op == "or":
            left = evaluate_expression(ctx, expr.left)
            if not isinstance(left, bool):
                raise Namel3ssError("Left operand of 'or' must be boolean", line=expr.line, column=expr.column)
            if left:
                return True
            right = evaluate_expression(ctx, expr.right)
            if not isinstance(right, bool):
                raise Namel3ssError("Right operand of 'or' must be boolean", line=expr.line, column=expr.column)
            return bool(right)
        raise Namel3ssError(f"Unsupported binary op '{expr.op}'", line=expr.line, column=expr.column)
    if isinstance(expr, ir.Comparison):
        left = evaluate_expression(ctx, expr.left)
        right = evaluate_expression(ctx, expr.right)
        if expr.kind in {"gt", "lt"}:
            if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                raise Namel3ssError(
                    "Greater/less comparisons require numbers",
                    line=expr.line,
                    column=expr.column,
                )
            return left > right if expr.kind == "gt" else left < right
        if expr.kind == "eq":
            return left == right
        raise Namel3ssError(f"Unsupported comparison '{expr.kind}'", line=expr.line, column=expr.column)

    raise Namel3ssError(f"Unsupported expression type: {type(expr)}", line=expr.line, column=expr.column)


def resolve_state_path(ctx: ExecutionContext, expr: ir.StatePath) -> object:
    cursor: object = ctx.state
    for segment in expr.path:
        if not isinstance(cursor, dict):
            raise Namel3ssError(
                f"State path '{'.'.join(expr.path)}' is not a mapping",
                line=expr.line,
                column=expr.column,
            )
        if segment not in cursor:
            raise Namel3ssError(
                f"Unknown state path '{'.'.join(expr.path)}'",
                line=expr.line,
                column=expr.column,
            )
        cursor = cursor[segment]
    return cursor
