from __future__ import annotations

from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.explain import ExpressionExplainCollector
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.utils.numbers import is_number, to_decimal


def eval_unary_op(
    ctx,
    expr: ir.UnaryOp,
    collector: ExpressionExplainCollector | None,
    eval_expr,
) -> object:
    operand = eval_expr(ctx, expr.operand, collector)
    if expr.op == "not":
        if not isinstance(operand, bool):
            raise Namel3ssError(
                _boolean_operand_message("not", operand),
                line=expr.line,
                column=expr.column,
            )
        result = not operand
        if collector:
            collector.record_unary(expr.op, operand, result)
        return result
    if expr.op in {"+", "-"}:
        if not is_number(operand):
            raise Namel3ssError(
                _arithmetic_type_message(expr.op, operand, None),
                line=expr.line,
                column=expr.column,
            )
        value = to_decimal(operand)
        result = value if expr.op == "+" else -value
        if collector:
            collector.record_unary(expr.op, operand, result)
        return result
    raise Namel3ssError(f"Unsupported unary op '{expr.op}'", line=expr.line, column=expr.column)


def eval_binary_op(
    ctx,
    expr: ir.BinaryOp,
    collector: ExpressionExplainCollector | None,
    eval_expr,
) -> object:
    if expr.op == "and":
        left = eval_expr(ctx, expr.left, collector)
        if not isinstance(left, bool):
            raise Namel3ssError(
                _boolean_operand_message("and", left),
                line=expr.line,
                column=expr.column,
            )
        if not left:
            if collector:
                collector.record_boolean(expr.op, left, None, False, short_circuit=True)
            return False
        right = eval_expr(ctx, expr.right, collector)
        if not isinstance(right, bool):
            raise Namel3ssError(
                _boolean_operand_message("and", right),
                line=expr.line,
                column=expr.column,
            )
        result = left and right
        if collector:
            collector.record_boolean(expr.op, left, right, result)
        return result
    if expr.op == "or":
        left = eval_expr(ctx, expr.left, collector)
        if not isinstance(left, bool):
            raise Namel3ssError(
                _boolean_operand_message("or", left),
                line=expr.line,
                column=expr.column,
            )
        if left:
            if collector:
                collector.record_boolean(expr.op, left, None, True, short_circuit=True)
            return True
        right = eval_expr(ctx, expr.right, collector)
        if not isinstance(right, bool):
            raise Namel3ssError(
                _boolean_operand_message("or", right),
                line=expr.line,
                column=expr.column,
            )
        result = bool(right)
        if collector:
            collector.record_boolean(expr.op, left, right, result)
        return result
    if expr.op in {"+", "-", "*", "/", "%", "**"}:
        left = eval_expr(ctx, expr.left, collector)
        right = eval_expr(ctx, expr.right, collector)
        if not is_number(left) or not is_number(right):
            raise Namel3ssError(
                _arithmetic_type_message(expr.op, left, right),
                line=expr.line,
                column=expr.column,
            )
        left_num = to_decimal(left)
        right_num = to_decimal(right)
        if expr.op == "+":
            result = left_num + right_num
            if collector:
                collector.record_binary(expr.op, left, right, result)
            return result
        if expr.op == "-":
            result = left_num - right_num
            if collector:
                collector.record_binary(expr.op, left, right, result)
            return result
        if expr.op == "*":
            result = left_num * right_num
            if collector:
                collector.record_binary(expr.op, left, right, result)
            return result
        if expr.op == "/":
            if right_num == Decimal("0"):
                raise Namel3ssError(
                    _division_by_zero_message(),
                    line=expr.line,
                    column=expr.column,
                )
            result = left_num / right_num
            if collector:
                collector.record_binary(expr.op, left, right, result)
            return result
        if expr.op == "%":
            if right_num == Decimal("0"):
                raise Namel3ssError(
                    _modulo_by_zero_message(),
                    line=expr.line,
                    column=expr.column,
                )
            result = left_num % right_num
            if collector:
                collector.record_binary(expr.op, left, right, result)
            return result
        if expr.op == "**":
            result = left_num ** right_num
            if collector:
                collector.record_binary(expr.op, left, right, result)
            return result
    raise Namel3ssError(f"Unsupported binary op '{expr.op}'", line=expr.line, column=expr.column)


def eval_comparison(
    ctx,
    expr: ir.Comparison,
    collector: ExpressionExplainCollector | None,
    eval_expr,
) -> object:
    left = eval_expr(ctx, expr.left, collector)
    right = eval_expr(ctx, expr.right, collector)
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
            result = left_num > right_num
            if collector:
                collector.record_comparison(expr.kind, left, right, result)
            return result
        if expr.kind == "lt":
            result = left_num < right_num
            if collector:
                collector.record_comparison(expr.kind, left, right, result)
            return result
        if expr.kind == "gte":
            result = left_num >= right_num
            if collector:
                collector.record_comparison(expr.kind, left, right, result)
            return result
        result = left_num <= right_num
        if collector:
            collector.record_comparison(expr.kind, left, right, result)
        return result
    if expr.kind == "eq":
        if is_number(left) and is_number(right):
            result = to_decimal(left) == to_decimal(right)
            if collector:
                collector.record_comparison(expr.kind, left, right, result)
            return result
        result = left == right
        if collector:
            collector.record_comparison(expr.kind, left, right, result)
        return result
    if expr.kind == "ne":
        if is_number(left) and is_number(right):
            result = to_decimal(left) != to_decimal(right)
            if collector:
                collector.record_comparison(expr.kind, left, right, result)
            return result
        result = left != right
        if collector:
            collector.record_comparison(expr.kind, left, right, result)
        return result
    raise Namel3ssError(f"Unsupported comparison '{expr.kind}'", line=expr.line, column=expr.column)


def _value_kind(value: object) -> str:
    return type_name_for_value(value)


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


def _modulo_by_zero_message() -> str:
    return build_guidance_message(
        what="Modulo by zero.",
        why="The right-hand side of '%' evaluated to 0.",
        fix="Check for zero before modulo.",
        example="if divisor is not equal to 0: set state.remainder is total % divisor",
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
        fix="Use a boolean expression. Comparisons return true or false.",
        example="if total is greater than 10: return true",
    )


__all__ = ["eval_binary_op", "eval_comparison", "eval_unary_op"]
