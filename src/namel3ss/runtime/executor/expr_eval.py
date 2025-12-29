from __future__ import annotations

from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.utils.numbers import is_number, to_decimal
from namel3ss.runtime.tools.executor import execute_tool_call


def evaluate_expression(ctx: ExecutionContext, expr: ir.Expression) -> object:
    if isinstance(expr, ir.Literal):
        return expr.value
    if isinstance(expr, ir.VarReference):
        if expr.name == "identity":
            return ctx.identity
        if expr.name not in ctx.locals:
            raise Namel3ssError(
                f"Unknown variable '{expr.name}'",
                line=expr.line,
                column=expr.column,
            )
        return ctx.locals[expr.name]
    if isinstance(expr, ir.AttrAccess):
        if expr.base == "identity":
            value = ctx.identity
        else:
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
                    if expr.base == "identity":
                        raise Namel3ssError(
                            _identity_attribute_message(attr),
                            line=expr.line,
                            column=expr.column,
                        )
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
                raise Namel3ssError(
                    _boolean_operand_message("not", operand),
                    line=expr.line,
                    column=expr.column,
                )
            return not operand
        if expr.op in {"+", "-"}:
            if not is_number(operand):
                raise Namel3ssError(
                    _arithmetic_type_message(expr.op, operand, None),
                    line=expr.line,
                    column=expr.column,
                )
            value = to_decimal(operand)
            return value if expr.op == "+" else -value
        raise Namel3ssError(f"Unsupported unary op '{expr.op}'", line=expr.line, column=expr.column)
    if isinstance(expr, ir.BinaryOp):
        if expr.op == "and":
            left = evaluate_expression(ctx, expr.left)
            if not isinstance(left, bool):
                raise Namel3ssError(
                    _boolean_operand_message("and", left),
                    line=expr.line,
                    column=expr.column,
                )
            if not left:
                return False
            right = evaluate_expression(ctx, expr.right)
            if not isinstance(right, bool):
                raise Namel3ssError(
                    _boolean_operand_message("and", right),
                    line=expr.line,
                    column=expr.column,
                )
            return left and right
        if expr.op == "or":
            left = evaluate_expression(ctx, expr.left)
            if not isinstance(left, bool):
                raise Namel3ssError(
                    _boolean_operand_message("or", left),
                    line=expr.line,
                    column=expr.column,
                )
            if left:
                return True
            right = evaluate_expression(ctx, expr.right)
            if not isinstance(right, bool):
                raise Namel3ssError(
                    _boolean_operand_message("or", right),
                    line=expr.line,
                    column=expr.column,
                )
            return bool(right)
        if expr.op in {"+", "-", "*", "/"}:
            left = evaluate_expression(ctx, expr.left)
            right = evaluate_expression(ctx, expr.right)
            if not is_number(left) or not is_number(right):
                raise Namel3ssError(
                    _arithmetic_type_message(expr.op, left, right),
                    line=expr.line,
                    column=expr.column,
                )
            left_num = to_decimal(left)
            right_num = to_decimal(right)
            if expr.op == "+":
                return left_num + right_num
            if expr.op == "-":
                return left_num - right_num
            if expr.op == "*":
                return left_num * right_num
            if expr.op == "/":
                if right_num == Decimal("0"):
                    raise Namel3ssError(
                        _division_by_zero_message(),
                        line=expr.line,
                        column=expr.column,
                    )
                return left_num / right_num
        raise Namel3ssError(f"Unsupported binary op '{expr.op}'", line=expr.line, column=expr.column)
    if isinstance(expr, ir.Comparison):
        left = evaluate_expression(ctx, expr.left)
        right = evaluate_expression(ctx, expr.right)
        if expr.kind in {"gt", "lt", "gte", "lte"}:
            if not is_number(left) or not is_number(right):
                raise Namel3ssError(
                    _comparison_type_message(),
                    line=expr.line,
                    column=expr.column,
                )
            left_num = to_decimal(left)
            right_num = to_decimal(right)
            if expr.kind == "gt":
                return left_num > right_num
            if expr.kind == "lt":
                return left_num < right_num
            if expr.kind == "gte":
                return left_num >= right_num
            return left_num <= right_num
        if expr.kind == "eq":
            if is_number(left) and is_number(right):
                return to_decimal(left) == to_decimal(right)
            return left == right
        if expr.kind == "ne":
            if is_number(left) and is_number(right):
                return to_decimal(left) != to_decimal(right)
            return left != right
        raise Namel3ssError(f"Unsupported comparison '{expr.kind}'", line=expr.line, column=expr.column)
    if isinstance(expr, ir.ToolCallExpr):
        record_step(
            ctx,
            kind="tool_call",
            what=f"called tool {expr.tool_name}",
            data={"tool_name": expr.tool_name},
            line=expr.line,
            column=expr.column,
        )
        payload = {}
        for arg in expr.arguments:
            if arg.name in payload:
                raise Namel3ssError(
                    f"Duplicate tool input '{arg.name}'",
                    line=arg.line,
                    column=arg.column,
                )
            payload[arg.name] = evaluate_expression(ctx, arg.value)
        outcome = execute_tool_call(
            ctx,
            expr.tool_name,
            payload,
            line=expr.line,
            column=expr.column,
        )
        return outcome.result_value

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


def _value_kind(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if is_number(value):
        return "number"
    if isinstance(value, str):
        return "text"
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "list"
    return type(value).__name__


def _arithmetic_type_message(op: str, left: object, right: object | None) -> str:
    if right is None:
        kinds = _value_kind(left)
        return build_guidance_message(
            what=f"Unary '{op}' requires a number.",
            why=f"The operand is {kinds}, but arithmetic only works on numbers.",
            fix="Use a numeric value or remove the operator.",
            example="let total is -10.5",
        )
    left_kind = _value_kind(left)
    right_kind = _value_kind(right)
    return build_guidance_message(
        what=f"Cannot apply '{op}' to {left_kind} and {right_kind}.",
        why="Arithmetic operators only work on numbers.",
        fix="Convert both values to numbers or remove the operator.",
        example="let total is 10.5 + 2.25",
    )


def _division_by_zero_message() -> str:
    return build_guidance_message(
        what="Division by zero.",
        why="The right-hand side of '/' evaluated to 0.",
        fix="Check for zero before dividing.",
        example="if divisor is not equal to 0: set state.ratio is total / divisor",
    )


def _comparison_type_message() -> str:
    return build_guidance_message(
        what="Comparison requires numbers.",
        why="Comparisons like `is greater than`, `is at least`, or `is less than` only work on numbers.",
        fix="Ensure both sides evaluate to numbers.",
        example="if total is greater than 10.5:",
    )


def _boolean_operand_message(op: str, value: object) -> str:
    return build_guidance_message(
        what=f"Operator '{op}' requires a boolean.",
        why=f"The operand is {_value_kind(value)}, but boolean logic only works with true/false.",
        fix="Use a boolean expression (comparisons return true/false).",
        example="if total is greater than 10: return true",
    )


def _identity_attribute_message(attr: str) -> str:
    return build_guidance_message(
        what=f"Identity is missing '{attr}'.",
        why="The app referenced identity data that was not provided.",
        fix="Provide the field via N3_IDENTITY_* or N3_IDENTITY_JSON.",
        example="N3_IDENTITY_EMAIL=dev@example.com",
    )
