from __future__ import annotations

from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.context import CallFrame, ExecutionContext
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.utils.numbers import is_number, to_decimal
from namel3ss.runtime.tools.executor import execute_tool_call
from namel3ss.runtime.values.list_ops import list_append, list_get, list_length
from namel3ss.runtime.values.map_ops import map_get, map_keys, map_set
from namel3ss.runtime.values.coerce import require_type
from namel3ss.runtime.values.types import type_name_for_value


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
        if expr.op in {"+", "-", "*", "/", "%"}:
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
            if expr.op == "%":
                if right_num == Decimal("0"):
                    raise Namel3ssError(
                        _modulo_by_zero_message(),
                        line=expr.line,
                        column=expr.column,
                    )
                return left_num % right_num
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
        if getattr(ctx, "call_stack", []):
            raise Namel3ssError(
                "Functions cannot call tools",
                line=expr.line,
                column=expr.column,
            )
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
    if isinstance(expr, ir.ListExpr):
        return [evaluate_expression(ctx, item) for item in expr.items]
    if isinstance(expr, ir.MapExpr):
        result: dict = {}
        for entry in expr.entries:
            key = evaluate_expression(ctx, entry.key)
            if not isinstance(key, str):
                raise Namel3ssError(
                    f"Map key must be text but got {type_name_for_value(key)}",
                    line=entry.line,
                    column=entry.column,
                )
            if key in result:
                raise Namel3ssError(
                    f"Map key '{key}' is duplicated",
                    line=entry.line,
                    column=entry.column,
                )
            result[key] = evaluate_expression(ctx, entry.value)
        return result
    if isinstance(expr, ir.ListOpExpr):
        target = evaluate_expression(ctx, expr.target)
        if expr.kind == "length":
            return list_length(target, line=expr.line, column=expr.column)
        if expr.kind == "append":
            if expr.value is None:
                raise Namel3ssError("List append needs a value", line=expr.line, column=expr.column)
            value = evaluate_expression(ctx, expr.value)
            return list_append(target, value, line=expr.line, column=expr.column)
        if expr.kind == "get":
            if expr.index is None:
                raise Namel3ssError("List get needs an index", line=expr.line, column=expr.column)
            index = evaluate_expression(ctx, expr.index)
            return list_get(target, index, line=expr.line, column=expr.column)
        raise Namel3ssError("Unsupported list operation", line=expr.line, column=expr.column)
    if isinstance(expr, ir.MapOpExpr):
        target = evaluate_expression(ctx, expr.target)
        if expr.kind == "get":
            if expr.key is None:
                raise Namel3ssError("Map get needs a key", line=expr.line, column=expr.column)
            key = evaluate_expression(ctx, expr.key)
            return map_get(target, key, line=expr.line, column=expr.column)
        if expr.kind == "set":
            if expr.key is None or expr.value is None:
                raise Namel3ssError("Map set needs a key and value", line=expr.line, column=expr.column)
            key = evaluate_expression(ctx, expr.key)
            value = evaluate_expression(ctx, expr.value)
            return map_set(target, key, value, line=expr.line, column=expr.column)
        if expr.kind == "keys":
            return map_keys(target, line=expr.line, column=expr.column)
        raise Namel3ssError("Unsupported map operation", line=expr.line, column=expr.column)
    if isinstance(expr, ir.CallFunctionExpr):
        return _call_function(ctx, expr)

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


def _identity_attribute_message(attr: str) -> str:
    return build_guidance_message(
        what=f"Identity is missing '{attr}'.",
        why="The app referenced identity data that was not provided.",
        fix="Provide the field via N3_IDENTITY_* or N3_IDENTITY_JSON.",
        example="N3_IDENTITY_EMAIL=dev@example.com",
    )


def _call_function(ctx: ExecutionContext, expr: ir.CallFunctionExpr) -> object:
    if expr.function_name not in ctx.functions:
        raise Namel3ssError(
            f"Unknown function '{expr.function_name}'",
            line=expr.line,
            column=expr.column,
        )
    if any(frame.function_name == expr.function_name for frame in getattr(ctx, "call_stack", [])):
        raise Namel3ssError(
            "Function recursion is not allowed",
            line=expr.line,
            column=expr.column,
        )
    func = ctx.functions[expr.function_name]
    signature = func.signature
    args_by_name: dict[str, object] = {}
    for arg in expr.arguments:
        if arg.name in args_by_name:
            raise Namel3ssError(
                f"Duplicate function argument '{arg.name}'",
                line=arg.line,
                column=arg.column,
            )
        args_by_name[arg.name] = evaluate_expression(ctx, arg.value)
    for param in signature.inputs:
        if param.name not in args_by_name:
            raise Namel3ssError(
                f"Missing function input '{param.name}'",
                line=expr.line,
                column=expr.column,
            )
        require_type(args_by_name[param.name], param.type_name, line=expr.line, column=expr.column)
    extra_args = set(args_by_name.keys()) - {param.name for param in signature.inputs}
    if extra_args:
        name = sorted(extra_args)[0]
        raise Namel3ssError(
            f"Unknown function input '{name}'",
            line=expr.line,
            column=expr.column,
        )
    locals_snapshot = ctx.locals
    constants_snapshot = ctx.constants
    call_locals = {param.name: args_by_name[param.name] for param in signature.inputs}
    record_step(
        ctx,
        kind="function_enter",
        what=f"entered function {expr.function_name}",
        line=expr.line,
        column=expr.column,
    )
    ctx.locals = call_locals
    ctx.constants = set()
    ctx.call_stack.append(
        CallFrame(function_name=expr.function_name, locals=call_locals, return_target="value")
    )
    try:
        from namel3ss.runtime.executor.statements import execute_statement
        from namel3ss.runtime.executor.signals import _ReturnSignal

        for stmt in func.body:
            execute_statement(ctx, stmt)
    except _ReturnSignal as signal:
        result_value = signal.value
        _validate_function_output(signature, result_value, expr)
        record_step(
            ctx,
            kind="function_return",
            what=f"returned from {expr.function_name}",
            line=expr.line,
            column=expr.column,
        )
        return result_value
    except Exception as exc:
        record_step(
            ctx,
            kind="function_error",
            what=f"error in {expr.function_name}",
            line=expr.line,
            column=expr.column,
        )
        raise exc
    finally:
        ctx.locals = locals_snapshot
        ctx.constants = constants_snapshot
        if ctx.call_stack:
            ctx.call_stack.pop()
    raise Namel3ssError(
        f'Function "{expr.function_name}" ended without return',
        line=expr.line,
        column=expr.column,
    )


def _validate_function_output(signature: ir.FunctionSignature, value: object, expr: ir.CallFunctionExpr) -> None:
    if signature.outputs is None:
        return
    if not isinstance(value, dict):
        raise Namel3ssError(
            "Function return must be a map",
            line=expr.line,
            column=expr.column,
        )
    output_map: dict = dict(value)
    expected = {param.name: param for param in signature.outputs}
    for name, param in expected.items():
        if name not in output_map:
            if not param.required:
                continue
            raise Namel3ssError(
                f"Missing function output '{name}'",
                line=expr.line,
                column=expr.column,
            )
        require_type(output_map[name], param.type_name, line=expr.line, column=expr.column)
    extra_keys = set(output_map.keys()) - set(expected.keys())
    if extra_keys:
        name = sorted(extra_keys)[0]
        raise Namel3ssError(
            f"Unknown function output '{name}'",
            line=expr.line,
            column=expr.column,
        )
