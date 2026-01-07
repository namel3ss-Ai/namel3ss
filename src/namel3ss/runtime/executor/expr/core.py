from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.context import CallFrame, ExecutionContext
from namel3ss.runtime.execution.explain import ExpressionExplainCollector
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.expr.lists import (
    eval_list_filter_expr,
    eval_list_map_expr,
    eval_list_op_expr,
    eval_list_reduce_expr,
    eval_map_op_expr,
)
from namel3ss.runtime.executor.expr.ops import eval_binary_op, eval_comparison, eval_unary_op
from namel3ss.runtime.tools.executor import execute_tool_call
from namel3ss.runtime.values.coerce import require_type
from namel3ss.runtime.values.types import type_name_for_value


def evaluate_expression(
    ctx: ExecutionContext,
    expr: ir.Expression,
    collector: ExpressionExplainCollector | None = None,
) -> object:
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
        return eval_unary_op(ctx, expr, collector, evaluate_expression)
    if isinstance(expr, ir.BinaryOp):
        return eval_binary_op(ctx, expr, collector, evaluate_expression)
    if isinstance(expr, ir.Comparison):
        return eval_comparison(ctx, expr, collector, evaluate_expression)
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
            payload[arg.name] = evaluate_expression(ctx, arg.value, collector)
        outcome = execute_tool_call(
            ctx,
            expr.tool_name,
            payload,
            line=expr.line,
            column=expr.column,
        )
        return outcome.result_value
    if isinstance(expr, ir.ListExpr):
        return [evaluate_expression(ctx, item, collector) for item in expr.items]
    if isinstance(expr, ir.MapExpr):
        result: dict = {}
        for entry in expr.entries:
            key = evaluate_expression(ctx, entry.key, collector)
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
            result[key] = evaluate_expression(ctx, entry.value, collector)
        return result
    if isinstance(expr, ir.ListOpExpr):
        return eval_list_op_expr(ctx, expr, collector, evaluate_expression)
    if isinstance(expr, ir.ListMapExpr):
        return eval_list_map_expr(ctx, expr, collector, evaluate_expression)
    if isinstance(expr, ir.ListFilterExpr):
        return eval_list_filter_expr(ctx, expr, collector, evaluate_expression)
    if isinstance(expr, ir.ListReduceExpr):
        return eval_list_reduce_expr(ctx, expr, collector, evaluate_expression)
    if isinstance(expr, ir.MapOpExpr):
        return eval_map_op_expr(ctx, expr, collector, evaluate_expression)
    if isinstance(expr, ir.CallFunctionExpr):
        return _call_function(ctx, expr, collector)

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


def _identity_attribute_message(attr: str) -> str:
    return build_guidance_message(
        what=f"Identity is missing '{attr}'.",
        why="The app referenced identity data that was not provided.",
        fix="Provide the field via N3_IDENTITY_* or N3_IDENTITY_JSON.",
        example="N3_IDENTITY_EMAIL=dev@example.com",
    )


def _call_function(
    ctx: ExecutionContext,
    expr: ir.CallFunctionExpr,
    collector: ExpressionExplainCollector | None = None,
) -> object:
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
        args_by_name[arg.name] = evaluate_expression(ctx, arg.value, collector)
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


__all__ = ["evaluate_expression", "resolve_state_path"]
