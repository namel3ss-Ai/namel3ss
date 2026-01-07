from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.explain import ExpressionExplainCollector
from namel3ss.runtime.values.list_ops import (
    list_append,
    list_get,
    list_length,
    list_max,
    list_mean,
    list_median,
    list_min,
    list_sum,
)
from namel3ss.runtime.values.map_ops import map_get, map_keys, map_set


def eval_list_op_expr(
    ctx,
    expr: ir.ListOpExpr,
    collector: ExpressionExplainCollector | None,
    eval_expr,
) -> object:
    target = eval_expr(ctx, expr.target, collector)
    if expr.kind == "length":
        result = list_length(target, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op(expr.kind, target, result)
        return result
    if expr.kind == "sum":
        result = list_sum(target, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op(expr.kind, target, result)
        return result
    if expr.kind == "min":
        result = list_min(target, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op(expr.kind, target, result)
        return result
    if expr.kind == "max":
        result = list_max(target, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op(expr.kind, target, result)
        return result
    if expr.kind == "mean":
        result = list_mean(target, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op(expr.kind, target, result)
        return result
    if expr.kind == "median":
        result = list_median(target, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op(expr.kind, target, result)
        return result
    if expr.kind == "append":
        if expr.value is None:
            raise Namel3ssError("List append needs a value", line=expr.line, column=expr.column)
        value = eval_expr(ctx, expr.value, collector)
        result = list_append(target, value, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op(expr.kind, target, result, value=value)
        return result
    if expr.kind == "get":
        if expr.index is None:
            raise Namel3ssError("List get needs an index", line=expr.line, column=expr.column)
        index = eval_expr(ctx, expr.index, collector)
        result = list_get(target, index, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op(expr.kind, target, result, index=index)
        return result
    raise Namel3ssError("Unsupported list operation", line=expr.line, column=expr.column)


def eval_list_map_expr(
    ctx,
    expr: ir.ListMapExpr,
    collector: ExpressionExplainCollector | None,
    eval_expr,
) -> object:
    target = eval_expr(ctx, expr.target, collector)
    if not isinstance(target, list):
        raise Namel3ssError(
            _list_expected_message("map"),
            line=expr.line,
            column=expr.column,
            details={"error_id": "lists.expected_list", "operation": "map"},
        )
    results: list[object] = []
    item_samples: list[dict] = []
    sample_limit = collector.sample_limit if collector else 0
    var_name = expr.var_name
    had_prev = var_name in ctx.locals
    prev_value = ctx.locals.get(var_name)
    try:
        for idx, item in enumerate(target):
            ctx.locals[var_name] = item
            result_item = eval_expr(ctx, expr.body, None)
            results.append(result_item)
            if collector and idx < sample_limit:
                item_samples.append(
                    {
                        "index": idx,
                        "input": item,
                        "output": result_item,
                    }
                )
    finally:
        if had_prev:
            ctx.locals[var_name] = prev_value
        else:
            ctx.locals.pop(var_name, None)
    if collector:
        collector.record_map(item_samples, target, results)
    return results


def eval_list_filter_expr(
    ctx,
    expr: ir.ListFilterExpr,
    collector: ExpressionExplainCollector | None,
    eval_expr,
) -> object:
    target = eval_expr(ctx, expr.target, collector)
    if not isinstance(target, list):
        raise Namel3ssError(
            _list_expected_message("filter"),
            line=expr.line,
            column=expr.column,
            details={"error_id": "lists.expected_list", "operation": "filter"},
        )
    results: list[object] = []
    item_samples: list[dict] = []
    sample_limit = collector.sample_limit if collector else 0
    var_name = expr.var_name
    had_prev = var_name in ctx.locals
    prev_value = ctx.locals.get(var_name)
    try:
        for idx, item in enumerate(target):
            ctx.locals[var_name] = item
            predicate = eval_expr(ctx, expr.predicate, None)
            if not isinstance(predicate, bool):
                line = getattr(expr.predicate, "line", None) or expr.line
                column = getattr(expr.predicate, "column", None) or expr.column
                raise Namel3ssError(
                    _filter_boolean_message(),
                    line=line,
                    column=column,
                    details={"error_id": "lists.expected_boolean"},
                )
            if predicate:
                results.append(item)
            if collector and idx < sample_limit:
                item_samples.append(
                    {
                        "index": idx,
                        "input": item,
                        "predicate": predicate,
                        "kept": predicate,
                    }
                )
    finally:
        if had_prev:
            ctx.locals[var_name] = prev_value
        else:
            ctx.locals.pop(var_name, None)
    if collector:
        collector.record_filter(item_samples, target, results)
    return results


def eval_list_reduce_expr(
    ctx,
    expr: ir.ListReduceExpr,
    collector: ExpressionExplainCollector | None,
    eval_expr,
) -> object:
    _reject_tool_calls_in_expr(expr.target)
    _reject_tool_calls_in_expr(expr.start)
    _reject_tool_calls_in_expr(expr.body)
    target = eval_expr(ctx, expr.target, collector)
    if not isinstance(target, list):
        raise Namel3ssError(
            _list_expected_message("reduce"),
            line=expr.line,
            column=expr.column,
            details={"error_id": "lists.expected_list", "operation": "reduce"},
        )
    acc_name = expr.acc_name
    item_name = expr.item_name
    acc_value = eval_expr(ctx, expr.start, collector)
    start_value = acc_value
    item_samples: list[dict] = []
    sample_limit = collector.sample_limit if collector else 0
    had_acc = acc_name in ctx.locals
    had_item = item_name in ctx.locals
    prev_acc = ctx.locals.get(acc_name)
    prev_item = ctx.locals.get(item_name)
    try:
        for idx, item in enumerate(target):
            ctx.locals[acc_name] = acc_value
            ctx.locals[item_name] = item
            next_value = eval_expr(ctx, expr.body, None)
            if collector and idx < sample_limit:
                item_samples.append(
                    {
                        "index": idx,
                        "acc": acc_value,
                        "item": item,
                        "result": next_value,
                    }
                )
            acc_value = next_value
    finally:
        if had_acc:
            ctx.locals[acc_name] = prev_acc
        else:
            ctx.locals.pop(acc_name, None)
        if had_item:
            ctx.locals[item_name] = prev_item
        else:
            ctx.locals.pop(item_name, None)
    if collector:
        collector.record_reduce(item_samples, target, start_value, acc_value)
    return acc_value


def eval_map_op_expr(
    ctx,
    expr: ir.MapOpExpr,
    collector: ExpressionExplainCollector | None,
    eval_expr,
) -> object:
    target = eval_expr(ctx, expr.target, collector)
    if expr.kind == "get":
        if expr.key is None:
            raise Namel3ssError("Map get needs a key", line=expr.line, column=expr.column)
        key = eval_expr(ctx, expr.key, collector)
        result = map_get(target, key, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op("map_get", target, result, value=key)
        return result
    if expr.kind == "set":
        if expr.key is None or expr.value is None:
            raise Namel3ssError("Map set needs a key and value", line=expr.line, column=expr.column)
        key = eval_expr(ctx, expr.key, collector)
        value = eval_expr(ctx, expr.value, collector)
        result = map_set(target, key, value, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op("map_set", target, result, value={"key": key, "value": value})
        return result
    if expr.kind == "keys":
        result = map_keys(target, line=expr.line, column=expr.column)
        if collector:
            collector.record_list_op("map_keys", target, result)
        return result
    raise Namel3ssError("Unsupported map operation", line=expr.line, column=expr.column)


def _list_expected_message(op_name: str) -> str:
    return build_guidance_message(
        what=f"{op_name} expects a list.",
        why="List transforms can only iterate list values.",
        fix="Pass a list value to the transform.",
        example=f"let result is {op_name} numbers with item as n:\n  n",
    )


def _filter_boolean_message() -> str:
    return build_guidance_message(
        what="Filter predicate must return a boolean.",
        why="Filter expressions include an item only when the predicate evaluates to true or false.",
        fix="Return a boolean condition from the predicate block.",
        example="let big is filter numbers with item as n:\n  n is greater than 10",
    )


def _reject_tool_calls_in_expr(expr: ir.Expression) -> None:
    if isinstance(expr, ir.ToolCallExpr):
        raise Namel3ssError(
            "Reduce expressions cannot call tools",
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ir.CallFunctionExpr):
        for arg in expr.arguments:
            _reject_tool_calls_in_expr(arg.value)
        return
    if isinstance(expr, ir.UnaryOp):
        _reject_tool_calls_in_expr(expr.operand)
        return
    if isinstance(expr, ir.BinaryOp):
        _reject_tool_calls_in_expr(expr.left)
        _reject_tool_calls_in_expr(expr.right)
        return
    if isinstance(expr, ir.Comparison):
        _reject_tool_calls_in_expr(expr.left)
        _reject_tool_calls_in_expr(expr.right)
        return
    if isinstance(expr, ir.ListExpr):
        for item in expr.items:
            _reject_tool_calls_in_expr(item)
        return
    if isinstance(expr, ir.MapExpr):
        for entry in expr.entries:
            _reject_tool_calls_in_expr(entry.key)
            _reject_tool_calls_in_expr(entry.value)
        return
    if isinstance(expr, ir.ListOpExpr):
        _reject_tool_calls_in_expr(expr.target)
        if expr.value is not None:
            _reject_tool_calls_in_expr(expr.value)
        if expr.index is not None:
            _reject_tool_calls_in_expr(expr.index)
        return
    if isinstance(expr, ir.MapOpExpr):
        _reject_tool_calls_in_expr(expr.target)
        if expr.key is not None:
            _reject_tool_calls_in_expr(expr.key)
        if expr.value is not None:
            _reject_tool_calls_in_expr(expr.value)
        return
    if isinstance(expr, ir.ListMapExpr):
        _reject_tool_calls_in_expr(expr.target)
        _reject_tool_calls_in_expr(expr.body)
        return
    if isinstance(expr, ir.ListFilterExpr):
        _reject_tool_calls_in_expr(expr.target)
        _reject_tool_calls_in_expr(expr.predicate)
        return
    if isinstance(expr, ir.ListReduceExpr):
        _reject_tool_calls_in_expr(expr.target)
        _reject_tool_calls_in_expr(expr.start)
        _reject_tool_calls_in_expr(expr.body)
        return


__all__ = [
    "eval_list_filter_expr",
    "eval_list_map_expr",
    "eval_list_op_expr",
    "eval_list_reduce_expr",
    "eval_map_op_expr",
]
