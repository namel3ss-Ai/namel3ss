from __future__ import annotations

import json
from decimal import Decimal
from typing import Iterable

from namel3ss.ir import nodes as ir
from namel3ss.traces.schema import TRACE_VERSION, TraceEventType
from namel3ss.utils.numbers import decimal_is_int, decimal_to_str

EXPLAIN_SAMPLE_LIMIT = 20

_PREC_OR = 1
_PREC_AND = 2
_PREC_COMPARE = 3
_PREC_ADD = 4
_PREC_MUL = 5
_PREC_UNARY = 6
_PREC_POWER = 7
_PREC_PRIMARY = 8


class ExpressionExplainCollector:
    def __init__(self, *, sample_limit: int = EXPLAIN_SAMPLE_LIMIT) -> None:
        self.sample_limit = sample_limit
        self.steps: list[dict] = []
        self.truncated = False

    def record_unary(self, op: str, operand: object, result: object) -> None:
        self._record(
            "unary_op",
            op=op,
            operand=_safe_value(operand),
            result=_safe_value(result),
        )

    def record_binary(self, op: str, left: object, right: object, result: object) -> None:
        self._record(
            "binary_op",
            op=op,
            left=_safe_value(left),
            right=_safe_value(right),
            result=_safe_value(result),
        )

    def record_boolean(
        self,
        op: str,
        left: object,
        right: object | None,
        result: object,
        *,
        short_circuit: bool = False,
    ) -> None:
        payload = {
            "op": op,
            "left": _safe_value(left),
            "result": _safe_value(result),
        }
        if right is not None:
            payload["right"] = _safe_value(right)
        if short_circuit:
            payload["short_circuit"] = True
        self._record("boolean_op", **payload)

    def record_comparison(self, op: str, left: object, right: object, result: object) -> None:
        self._record(
            "comparison",
            op=op,
            left=_safe_value(left),
            right=_safe_value(right),
            result=_safe_value(result),
        )

    def record_list_op(
        self,
        op: str,
        target: object,
        result: object,
        *,
        value: object | None = None,
        index: object | None = None,
    ) -> None:
        payload: dict[str, object] = {"op": op}
        if isinstance(target, list):
            sample, truncated = _sample_list(target, self.sample_limit)
            payload["input_count"] = len(target)
            payload["input_sample"] = sample
            if truncated:
                payload["input_truncated"] = True
                self.truncated = True
        else:
            payload["input"] = _safe_value(target)
        if value is not None:
            payload["value"] = _safe_value(value)
        if index is not None:
            payload["index"] = _safe_value(index)
        payload["result"] = _safe_value(result)
        kind = "aggregation" if op in {"sum", "min", "max", "mean", "median"} else "list_op"
        self._record(kind, **payload)

    def record_map(self, items: list[dict], target: list, results: list) -> None:
        input_sample, input_truncated = _sample_list(target, self.sample_limit)
        output_sample, output_truncated = _sample_list(results, self.sample_limit)
        truncated = input_truncated or output_truncated or len(target) > len(items)
        if truncated:
            self.truncated = True
        payload = {
            "input_count": len(target),
            "input_sample": input_sample,
            "output_count": len(results),
            "output_sample": output_sample,
            "items": _safe_items(items),
        }
        if truncated:
            payload["truncated"] = True
        self._record("map", **payload)

    def record_filter(self, items: list[dict], target: list, results: list) -> None:
        input_sample, input_truncated = _sample_list(target, self.sample_limit)
        output_sample, output_truncated = _sample_list(results, self.sample_limit)
        truncated = input_truncated or output_truncated or len(target) > len(items)
        if truncated:
            self.truncated = True
        payload = {
            "input_count": len(target),
            "input_sample": input_sample,
            "output_count": len(results),
            "output_sample": output_sample,
            "items": _safe_items(items),
        }
        if truncated:
            payload["truncated"] = True
        self._record("filter", **payload)

    def record_reduce(
        self,
        items: list[dict],
        target: list,
        start_value: object,
        result: object,
    ) -> None:
        input_sample, input_truncated = _sample_list(target, self.sample_limit)
        truncated = input_truncated or len(target) > len(items)
        if truncated:
            self.truncated = True
        payload = {
            "input_count": len(target),
            "input_sample": input_sample,
            "start": _safe_value(start_value),
            "result": _safe_value(result),
            "items": _safe_items(items),
        }
        if truncated:
            payload["truncated"] = True
        self._record("reduce", **payload)

    def _record(self, kind: str, **payload: object) -> None:
        entry = {"kind": kind}
        entry.update(payload)
        self.steps.append(entry)


def build_expression_explain_trace(
    *,
    target: str,
    expression: str,
    result: object,
    steps: Iterable[dict],
    span: dict[str, int | None],
    assignment_kind: str,
    flow_name: str | None,
    sample_limit: int,
    truncated: bool,
) -> dict:
    result_value, result_count, result_truncated = _coerce_result_value(result, sample_limit)
    trace = {
        "type": TraceEventType.EXPRESSION_EXPLAIN,
        "trace_version": TRACE_VERSION,
        "title": f"Explain {target}",
        "target": target,
        "assignment_kind": assignment_kind,
        "expression": expression,
        "result": result_value,
        "steps": list(steps),
        "span": span,
    }
    if flow_name:
        trace["flow"] = flow_name
    if result_count is not None:
        trace["result_count"] = result_count
    if result_truncated:
        trace["result_truncated"] = True
    if truncated:
        trace["truncated"] = True
    return trace


def format_expression_canonical(expr: ir.Expression) -> str:
    text, _ = _format_expr(expr, parent_prec=0, position=None, parent_op=None)
    return text


def _format_expr(
    expr: ir.Expression,
    *,
    parent_prec: int,
    position: str | None,
    parent_op: str | None,
) -> tuple[str, int]:
    between = _format_between(expr)
    if between:
        text, prec = between
        return _wrap_if_needed(text, prec, parent_prec, position, parent_op), prec

    if isinstance(expr, ir.Literal):
        return _format_literal(expr.value), _PREC_PRIMARY
    if isinstance(expr, ir.VarReference):
        return expr.name, _PREC_PRIMARY
    if isinstance(expr, ir.AttrAccess):
        return ".".join([expr.base, *expr.attrs]), _PREC_PRIMARY
    if isinstance(expr, ir.StatePath):
        return "state." + ".".join(expr.path), _PREC_PRIMARY
    if isinstance(expr, ir.ToolCallExpr):
        return _format_tool_call(expr), _PREC_PRIMARY
    if isinstance(expr, ir.CallFunctionExpr):
        return _format_function_call(expr), _PREC_PRIMARY
    if isinstance(expr, ir.ListExpr):
        return _format_list_literal(expr), _PREC_PRIMARY
    if isinstance(expr, ir.MapExpr):
        return _format_map_literal(expr), _PREC_PRIMARY
    if isinstance(expr, ir.ListOpExpr):
        return _format_list_op(expr), _PREC_PRIMARY
    if isinstance(expr, ir.MapOpExpr):
        return _format_map_op(expr), _PREC_PRIMARY
    if isinstance(expr, ir.ListMapExpr):
        return _format_list_transform("map", expr.target, expr.var_name, expr.body), _PREC_PRIMARY
    if isinstance(expr, ir.ListFilterExpr):
        return _format_list_transform("filter", expr.target, expr.var_name, expr.predicate), _PREC_PRIMARY
    if isinstance(expr, ir.ListReduceExpr):
        return _format_reduce(expr), _PREC_PRIMARY
    if isinstance(expr, ir.UnaryOp):
        operand_text, _ = _format_expr(
            expr.operand,
            parent_prec=_PREC_UNARY,
            position="right",
            parent_op=expr.op,
        )
        return f"{expr.op} {operand_text}", _PREC_UNARY
    if isinstance(expr, ir.Comparison):
        left_text, _ = _format_expr(expr.left, parent_prec=_PREC_COMPARE, position="left", parent_op=None)
        right_text, _ = _format_expr(expr.right, parent_prec=_PREC_COMPARE, position="right", parent_op=None)
        text = f"{left_text} {_comparison_text(expr.kind)} {right_text}"
        return _wrap_if_needed(text, _PREC_COMPARE, parent_prec, position, parent_op), _PREC_COMPARE
    if isinstance(expr, ir.BinaryOp):
        prec = _binary_prec(expr.op)
        left_text, _ = _format_expr(expr.left, parent_prec=prec, position="left", parent_op=expr.op)
        right_text, _ = _format_expr(expr.right, parent_prec=prec, position="right", parent_op=expr.op)
        text = f"{left_text} {expr.op} {right_text}"
        return _wrap_if_needed(text, prec, parent_prec, position, parent_op), prec
    return "expression", _PREC_PRIMARY


def _wrap_if_needed(text: str, prec: int, parent_prec: int, position: str | None, parent_op: str | None) -> str:
    if prec < parent_prec:
        return f"({text})"
    if prec == parent_prec and position and parent_op:
        if parent_op == "**":
            if position == "left":
                return f"({text})"
        else:
            if position == "right":
                return f"({text})"
    return text


def _binary_prec(op: str) -> int:
    if op == "or":
        return _PREC_OR
    if op == "and":
        return _PREC_AND
    if op in {"+", "-"}:
        return _PREC_ADD
    if op in {"*", "/", "%"}:
        return _PREC_MUL
    if op == "**":
        return _PREC_POWER
    return _PREC_ADD


def _format_between(expr: ir.Expression) -> tuple[str, int] | None:
    if not isinstance(expr, ir.BinaryOp) or expr.op != "and":
        return None
    left_cmp = expr.left if isinstance(expr.left, ir.Comparison) else None
    right_cmp = expr.right if isinstance(expr.right, ir.Comparison) else None
    if not left_cmp or not right_cmp:
        return None
    if not _expr_equal(left_cmp.left, right_cmp.left):
        return None
    lower_cmp = left_cmp if left_cmp.kind in {"gt", "gte"} else None
    upper_cmp = right_cmp if right_cmp.kind in {"lt", "lte"} else None
    if lower_cmp is None or upper_cmp is None:
        lower_cmp = right_cmp if right_cmp.kind in {"gt", "gte"} else None
        upper_cmp = left_cmp if left_cmp.kind in {"lt", "lte"} else None
    if lower_cmp is None or upper_cmp is None:
        return None
    strict = lower_cmp.kind == "gt" and upper_cmp.kind == "lt"
    if not strict and not (lower_cmp.kind == "gte" and upper_cmp.kind == "lte"):
        return None
    left_text, _ = _format_expr(lower_cmp.left, parent_prec=_PREC_COMPARE, position="left", parent_op=None)
    lower_text, _ = _format_expr(lower_cmp.right, parent_prec=_PREC_COMPARE, position="right", parent_op=None)
    upper_text, _ = _format_expr(upper_cmp.right, parent_prec=_PREC_COMPARE, position="right", parent_op=None)
    qualifier = "strictly " if strict else ""
    return f"{left_text} is {qualifier}between {lower_text} and {upper_text}", _PREC_COMPARE


def _expr_equal(left: ir.Expression, right: ir.Expression) -> bool:
    try:
        return left == right
    except Exception:
        return False


def _format_literal(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        if decimal_is_int(value):
            return str(int(value))
        return decimal_to_str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def _comparison_text(kind: str) -> str:
    return {
        "gt": "is greater than",
        "lt": "is less than",
        "gte": "is at least",
        "lte": "is at most",
        "eq": "is equal to",
        "ne": "is not equal to",
    }.get(kind, "is equal to")


def _format_tool_call(expr: ir.ToolCallExpr) -> str:
    if not expr.arguments:
        return f"{expr.tool_name}:"
    lines = [f"{expr.tool_name}:"]
    for arg in expr.arguments:
        line = f"{arg.name} is {format_expression_canonical(arg.value)}"
        lines.extend(_indent_block(line))
    return "\n".join(lines)


def _format_function_call(expr: ir.CallFunctionExpr) -> str:
    name = json.dumps(expr.function_name, ensure_ascii=True)
    if not expr.arguments:
        return f"call function {name}:"
    lines = [f"call function {name}:"]
    for arg in expr.arguments:
        line = f"{arg.name} is {format_expression_canonical(arg.value)}"
        lines.extend(_indent_block(line))
    return "\n".join(lines)


def _format_list_literal(expr: ir.ListExpr) -> str:
    if not expr.items:
        return "list:"
    lines = ["list:"]
    for item in expr.items:
        formatted = format_expression_canonical(item)
        lines.extend(_indent_block(formatted))
    return "\n".join(lines)


def _format_map_literal(expr: ir.MapExpr) -> str:
    if not expr.entries:
        return "map:"
    lines = ["map:"]
    for entry in expr.entries:
        key_text = format_expression_canonical(entry.key)
        value_text = format_expression_canonical(entry.value)
        line = f"{key_text} is {value_text}"
        lines.extend(_indent_block(line))
    return "\n".join(lines)


def _format_list_op(expr: ir.ListOpExpr) -> str:
    target = format_expression_canonical(expr.target)
    if expr.kind in {"sum", "min", "max", "mean", "median", "length"}:
        if expr.kind == "length":
            return f"list length of {target}"
        return f"{expr.kind}({target})"
    if expr.kind == "append":
        value = format_expression_canonical(expr.value) if expr.value is not None else "value"
        return f"list append {target} with {value}"
    if expr.kind == "get":
        index = format_expression_canonical(expr.index) if expr.index is not None else "index"
        return f"list get {target} at {index}"
    return f"list {expr.kind} {target}"


def _format_map_op(expr: ir.MapOpExpr) -> str:
    target = format_expression_canonical(expr.target)
    if expr.kind == "get":
        key = format_expression_canonical(expr.key) if expr.key is not None else "key"
        return f"map get {target} key {key}"
    if expr.kind == "set":
        key = format_expression_canonical(expr.key) if expr.key is not None else "key"
        value = format_expression_canonical(expr.value) if expr.value is not None else "value"
        return f"map set {target} key {key} value {value}"
    if expr.kind == "keys":
        return f"map keys {target}"
    return f"map {expr.kind} {target}"


def _format_list_transform(op: str, target: ir.Expression, var_name: str, body: ir.Expression) -> str:
    target_text = format_expression_canonical(target)
    body_text = format_expression_canonical(body)
    header = f"{op} {target_text} with item as {var_name}:"
    return "\n".join([header, *_indent_block(body_text)])


def _format_reduce(expr: ir.ListReduceExpr) -> str:
    target_text = format_expression_canonical(expr.target)
    start_text = format_expression_canonical(expr.start)
    body_text = format_expression_canonical(expr.body)
    header = (
        f"reduce {target_text} with acc as {expr.acc_name} "
        f"and item as {expr.item_name} starting {start_text}:"
    )
    return "\n".join([header, *_indent_block(body_text)])


def _indent_block(text: str, indent: str = "  ") -> list[str]:
    lines = text.splitlines() if text else [""]
    return [f"{indent}{line}" for line in lines]


def _safe_value(value: object) -> object:
    if isinstance(value, Decimal):
        return value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe_value(val) for key, val in value.items()}
    return str(value)


def _safe_items(items: list[dict]) -> list[dict]:
    safe: list[dict] = []
    for item in items:
        safe.append({str(key): _safe_value(val) for key, val in item.items()})
    return safe


def _sample_list(values: list, limit: int) -> tuple[list, bool]:
    truncated = len(values) > limit
    sample = [_safe_value(item) for item in values[:limit]]
    return sample, truncated


def _coerce_result_value(value: object, limit: int) -> tuple[object, int | None, bool]:
    if isinstance(value, list):
        sample, truncated = _sample_list(value, limit)
        return sample, len(value), truncated
    return _safe_value(value), None, False


__all__ = [
    "EXPLAIN_SAMPLE_LIMIT",
    "ExpressionExplainCollector",
    "build_expression_explain_trace",
    "format_expression_canonical",
]
