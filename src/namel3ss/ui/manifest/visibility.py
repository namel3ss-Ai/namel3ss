from __future__ import annotations

from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.utils.numbers import decimal_to_str, is_number, to_decimal
from namel3ss.validation import ValidationMode


def evaluate_visibility(
    visibility: ir.Expression | None,
    visibility_rule: ir.VisibilityRule | ir.VisibilityExpressionRule | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
    *,
    line: int | None,
    column: int | None,
) -> tuple[bool, dict | None]:
    if visibility is None and visibility_rule is None:
        return True, None
    if visibility is not None and visibility_rule is not None:
        raise Namel3ssError(
            "Visibility cannot combine visibility clauses with only-when rules.",
            line=line,
            column=column,
        )

    if isinstance(visibility_rule, ir.VisibilityRule):
        return _evaluate_legacy_visibility_rule(visibility_rule, state_ctx, line=line, column=column)

    if isinstance(visibility_rule, ir.VisibilityExpressionRule):
        result = _evaluate_boolean_expression(visibility_rule.expression, state_ctx, line=line, column=column)
        predicate = _render_expression(visibility_rule.expression)
        info = {
            "predicate": predicate,
            "state_paths": _collect_state_paths(visibility_rule.expression),
            "result": result,
        }
        return result, info

    if visibility is None:
        return True, None

    if isinstance(visibility, ir.StatePath):
        path = visibility.path
        label = f"state.{'.'.join(path)}"
        result = False
        if state_ctx.has_value(path):
            value, _ = state_ctx.value(path, default=None, register_default=False)
            result = bool(value)
        info = {"predicate": label, "state_paths": [label], "result": result}
        return result, info

    result = _evaluate_boolean_expression(visibility, state_ctx, line=line, column=column)
    predicate = _render_expression(visibility)
    info = {
        "predicate": predicate,
        "state_paths": _collect_state_paths(visibility),
        "result": result,
    }
    return result, info


def _evaluate_legacy_visibility_rule(
    visibility_rule: ir.VisibilityRule,
    state_ctx: StateContext,
    *,
    line: int | None,
    column: int | None,
) -> tuple[bool, dict | None]:
    path = getattr(visibility_rule.path, "path", None)
    if not isinstance(visibility_rule.path, ir.StatePath) or not path:
        raise Namel3ssError("Visibility rule requires state.<path> is <value>.", line=line, column=column)
    label = f"state.{'.'.join(path)}"
    if not state_ctx.declared(path):
        raise Namel3ssError(
            f"Visibility rule requires declared state path '{label}'.",
            line=line,
            column=column,
        )
    try:
        state_value, _ = state_ctx.value(path, default=None, register_default=False)
    except KeyError as err:
        raise Namel3ssError(
            f"Visibility rule requires declared state path '{label}'.",
            line=line,
            column=column,
        ) from err
    literal = visibility_rule.value
    if not isinstance(literal, ir.Literal):
        raise Namel3ssError("Visibility rule requires a text, number, or boolean value.", line=line, column=column)
    result = _evaluate_visibility_rule(label, state_value, literal.value, line=line, column=column)
    predicate = f"{label} is {_format_visibility_value(literal.value)}"
    info = {"predicate": predicate, "state_paths": [label], "result": result}
    return result, info


def _evaluate_boolean_expression(
    expr: ir.Expression,
    state_ctx: StateContext,
    *,
    line: int | None,
    column: int | None,
) -> bool:
    value = _evaluate_expression(expr, state_ctx, line=line, column=column)
    if not isinstance(value, bool):
        raise Namel3ssError(
            f"Visibility expression must evaluate to boolean, got {type_name_for_value(value)}.",
            line=line,
            column=column,
        )
    return value


def _evaluate_expression(expr: ir.Expression, state_ctx: StateContext, *, line: int | None, column: int | None) -> object:
    if isinstance(expr, ir.Literal):
        return expr.value
    if isinstance(expr, ir.StatePath):
        label = f"state.{'.'.join(expr.path)}"
        if state_ctx.has_value(expr.path):
            value, _ = state_ctx.value(expr.path, default=None, register_default=False)
            return value
        raise Namel3ssError(
            f"Visibility expression references unknown state path '{label}'.",
            line=line,
            column=column,
        )
    if isinstance(expr, ir.ListExpr):
        return [_evaluate_expression(item, state_ctx, line=line, column=column) for item in expr.items]
    if isinstance(expr, ir.UnaryOp):
        operand = _evaluate_expression(expr.operand, state_ctx, line=line, column=column)
        if expr.op != "not":
            raise Namel3ssError(
                f"Visibility expression does not support unary operator '{expr.op}'.",
                line=line,
                column=column,
            )
        if not isinstance(operand, bool):
            raise Namel3ssError(
                f"Visibility expression 'not' requires boolean but got {type_name_for_value(operand)}.",
                line=line,
                column=column,
            )
        return not operand
    if isinstance(expr, ir.BinaryOp):
        if expr.op == "and":
            left = _evaluate_expression(expr.left, state_ctx, line=line, column=column)
            if not isinstance(left, bool):
                raise Namel3ssError(
                    f"Visibility expression 'and' requires booleans but got {type_name_for_value(left)}.",
                    line=line,
                    column=column,
                )
            if not left:
                return False
            right = _evaluate_expression(expr.right, state_ctx, line=line, column=column)
            if not isinstance(right, bool):
                raise Namel3ssError(
                    f"Visibility expression 'and' requires booleans but got {type_name_for_value(right)}.",
                    line=line,
                    column=column,
                )
            return bool(right)
        if expr.op == "or":
            left = _evaluate_expression(expr.left, state_ctx, line=line, column=column)
            if not isinstance(left, bool):
                raise Namel3ssError(
                    f"Visibility expression 'or' requires booleans but got {type_name_for_value(left)}.",
                    line=line,
                    column=column,
                )
            if left:
                return True
            right = _evaluate_expression(expr.right, state_ctx, line=line, column=column)
            if not isinstance(right, bool):
                raise Namel3ssError(
                    f"Visibility expression 'or' requires booleans but got {type_name_for_value(right)}.",
                    line=line,
                    column=column,
                )
            return bool(right)
        raise Namel3ssError(
            f"Visibility expression does not support binary operator '{expr.op}'.",
            line=line,
            column=column,
        )
    if isinstance(expr, ir.Comparison):
        left = _evaluate_expression(expr.left, state_ctx, line=line, column=column)
        right = _evaluate_expression(expr.right, state_ctx, line=line, column=column)
        return _evaluate_comparison(expr.kind, left, right, line=line, column=column)
    raise Namel3ssError(
        "Visibility expression only supports literals, state paths, lists, comparisons, and boolean logic.",
        line=line,
        column=column,
    )


def _evaluate_comparison(kind: str, left: object, right: object, *, line: int | None, column: int | None) -> bool:
    if kind in {"gt", "lt", "gte", "lte"}:
        if not is_number(left) or not is_number(right):
            raise Namel3ssError(_comparison_type_message(), line=line, column=column)
        left_num = to_decimal(left)
        right_num = to_decimal(right)
        if kind == "gt":
            return left_num > right_num
        if kind == "lt":
            return left_num < right_num
        if kind == "gte":
            return left_num >= right_num
        return left_num <= right_num
    if kind == "eq":
        if is_number(left) and is_number(right):
            return to_decimal(left) == to_decimal(right)
        return left == right
    if kind == "ne":
        if is_number(left) and is_number(right):
            return to_decimal(left) != to_decimal(right)
        return left != right
    if kind == "in":
        if not isinstance(right, list):
            raise Namel3ssError("Visibility expression 'in' requires a list on the right side.", line=line, column=column)
        return left in right
    if kind == "nin":
        if not isinstance(right, list):
            raise Namel3ssError("Visibility expression 'not in' requires a list on the right side.", line=line, column=column)
        return left not in right
    raise Namel3ssError(f"Unsupported visibility comparison '{kind}'.", line=line, column=column)


def _collect_state_paths(expr: ir.Expression) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def _walk(node: ir.Expression) -> None:
        if isinstance(node, ir.StatePath):
            label = f"state.{'.'.join(node.path)}"
            if label not in seen:
                seen.add(label)
                ordered.append(label)
            return
        if isinstance(node, ir.UnaryOp):
            _walk(node.operand)
            return
        if isinstance(node, ir.BinaryOp):
            _walk(node.left)
            _walk(node.right)
            return
        if isinstance(node, ir.Comparison):
            _walk(node.left)
            _walk(node.right)
            return
        if isinstance(node, ir.ListExpr):
            for child in node.items:
                _walk(child)
            return

    _walk(expr)
    return ordered


def _render_expression(expr: ir.Expression) -> str:
    if isinstance(expr, ir.Literal):
        return _format_visibility_value(expr.value)
    if isinstance(expr, ir.StatePath):
        return f"state.{'.'.join(expr.path)}"
    if isinstance(expr, ir.ListExpr):
        inner = ", ".join(_render_expression(item) for item in expr.items)
        return f"[{inner}]"
    if isinstance(expr, ir.UnaryOp):
        return f"not {_render_expression(expr.operand)}"
    if isinstance(expr, ir.BinaryOp):
        return f"({_render_expression(expr.left)} {expr.op} {_render_expression(expr.right)})"
    if isinstance(expr, ir.Comparison):
        operator = {
            "eq": "==",
            "ne": "!=",
            "gt": ">",
            "lt": "<",
            "gte": ">=",
            "lte": "<=",
            "in": "in",
            "nin": "not in",
        }.get(expr.kind, expr.kind)
        return f"{_render_expression(expr.left)} {operator} {_render_expression(expr.right)}"
    return "<visibility_expression>"


def _evaluate_visibility_rule(label: str, state_value: object, literal_value: object, *, line: int | None, column: int | None) -> bool:
    if isinstance(literal_value, bool):
        if not isinstance(state_value, bool):
            raise Namel3ssError(
                _visibility_type_mismatch(label, "boolean", state_value),
                line=line,
                column=column,
            )
        return state_value is literal_value
    if is_number(literal_value):
        if not is_number(state_value):
            raise Namel3ssError(
                _visibility_type_mismatch(label, "number", state_value),
                line=line,
                column=column,
            )
        return to_decimal(state_value) == to_decimal(literal_value)
    if isinstance(literal_value, str):
        if not isinstance(state_value, str):
            raise Namel3ssError(
                _visibility_type_mismatch(label, "text", state_value),
                line=line,
                column=column,
            )
        return state_value == literal_value
    raise Namel3ssError(
        "Visibility rule requires a text, number, or boolean value.",
        line=line,
        column=column,
    )


def _comparison_type_message() -> str:
    return "Visibility comparisons with >, <, >=, <= require numbers on both sides."


def _visibility_type_mismatch(label: str, expected: str, actual_value: object) -> str:
    actual = type_name_for_value(actual_value)
    return f"Visibility rule for {label} expects {expected} but state value is {actual}."


def _format_visibility_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if is_number(value):
        if isinstance(value, Decimal):
            return decimal_to_str(value)
        return str(value)
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def apply_visibility(element: dict, visible: bool, info: dict | None) -> dict:
    if info is not None:
        element["visibility"] = info
        element["visible"] = bool(visible)
        return element
    if not visible:
        element["visible"] = False
    return element


def apply_show_when(element: dict, info: dict | None) -> dict:
    if info is not None:
        element["show_when"] = info
    return element


__all__ = ["apply_show_when", "apply_visibility", "evaluate_visibility"]
