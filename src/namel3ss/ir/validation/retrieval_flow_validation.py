from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.retrieval.tuning import (
    RETRIEVAL_TUNING_FLOWS,
    SET_FINAL_TOP_K,
    SET_LEXICAL_K,
    SET_SEMANTIC_K,
    SET_SEMANTIC_WEIGHT,
    normalize_retrieval_k,
    normalize_retrieval_weight,
)

_K_TUNING_FLOWS = {SET_SEMANTIC_K, SET_LEXICAL_K, SET_FINAL_TOP_K}
_NUMERIC_TYPE_NAMES = {"number", "int", "float"}


@dataclass(frozen=True)
class _Invocation:
    flow_name: str
    name: str
    expr: ir.BuiltinCallExpr


def validate_retrieval_flow_usage(
    flows: list[ir.Flow],
    flow_contracts: dict[str, ir.ContractDecl],
) -> dict[str, object]:
    flow_map = {flow.name: flow for flow in flows}
    by_flow: dict[str, list[_Invocation]] = {}
    for flow in flows:
        calls = list(_walk_flow_for_retrieval_calls(flow))
        by_flow[flow.name] = calls
        _validate_flow_invocations(flow, calls)
    controls = _build_controls(flow_map, flow_contracts, by_flow)
    invocations = _build_invocation_payload(by_flow)
    return {
        "controls": controls,
        "invocations": invocations,
    }


def _build_controls(
    flow_map: dict[str, ir.Flow],
    flow_contracts: dict[str, ir.ContractDecl],
    by_flow: dict[str, list[_Invocation]],
) -> dict[str, dict[str, object]]:
    controls: dict[str, dict[str, object]] = {}
    for flow_name in RETRIEVAL_TUNING_FLOWS:
        flow = flow_map.get(flow_name)
        if flow is None:
            controls[flow_name] = {
                "flow": flow_name,
                "available": False,
                "reason": f'Flow "{flow_name}" is not declared.',
            }
            continue
        calls = by_flow.get(flow_name) or []
        if not any(call.name == flow_name for call in calls):
            controls[flow_name] = {
                "flow": flow_name,
                "available": False,
                "reason": f'Flow "{flow_name}" does not call {flow_name}().',
            }
            continue
        contract = flow_contracts.get(flow_name)
        if contract is None:
            controls[flow_name] = {
                "flow": flow_name,
                "available": False,
                "reason": f'Flow "{flow_name}" is missing a contract.',
            }
            continue
        inputs = list(getattr(contract.signature, "inputs", []) or [])
        if len(inputs) != 1:
            controls[flow_name] = {
                "flow": flow_name,
                "available": False,
                "reason": f'Flow "{flow_name}" must declare exactly one numeric input.',
            }
            continue
        input_param = inputs[0]
        type_name = str(getattr(input_param, "type_name", "") or "").strip().lower()
        if type_name not in _NUMERIC_TYPE_NAMES:
            controls[flow_name] = {
                "flow": flow_name,
                "available": False,
                "reason": f'Flow "{flow_name}" input must be numeric.',
            }
            continue
        controls[flow_name] = {
            "flow": flow_name,
            "available": True,
            "input_field": str(getattr(input_param, "name", "") or ""),
            "input_type": type_name,
            "reason": "",
        }
    return controls


def _build_invocation_payload(by_flow: dict[str, list[_Invocation]]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for flow_name in sorted(by_flow.keys()):
        calls = by_flow.get(flow_name) or []
        for call in calls:
            if call.name not in set(RETRIEVAL_TUNING_FLOWS):
                continue
            payload.append(
                {
                    "flow": flow_name,
                    "name": call.name,
                    "line": call.expr.line,
                    "column": call.expr.column,
                }
            )
    return payload


def _validate_flow_invocations(flow: ir.Flow, invocations: list[_Invocation]) -> None:
    if not invocations:
        return
    supported: list[_Invocation] = []
    for call in invocations:
        if call.name not in set(RETRIEVAL_TUNING_FLOWS):
            raise Namel3ssError(
                f"UnknownFlowError: unsupported retrieval flow '{call.name}'.",
                line=call.expr.line,
                column=call.expr.column,
            )
        _validate_invocation_signature(call)
        supported.append(call)
    _validate_ordering(flow, supported)


def _validate_invocation_signature(call: _Invocation) -> None:
    expr = call.expr
    if len(expr.arguments) != 1:
        raise Namel3ssError(
            f"InvalidRetrievalParameterError: {call.name} expects exactly one argument.",
            line=expr.line,
            column=expr.column,
        )
    literal_ok, literal_value = _literal_value(expr.arguments[0])
    if not literal_ok:
        return
    try:
        if call.name in _K_TUNING_FLOWS:
            normalize_retrieval_k(literal_value, flow_name=call.name)
        else:
            normalize_retrieval_weight(literal_value, flow_name=call.name)
    except ValueError as exc:
        raise Namel3ssError(
            f"InvalidRetrievalParameterError: {exc}",
            line=expr.line,
            column=expr.column,
        ) from exc


def _validate_ordering(flow: ir.Flow, invocations: list[_Invocation]) -> None:
    has_semantic_k = any(call.name == SET_SEMANTIC_K for call in invocations)
    has_lexical_k = any(call.name == SET_LEXICAL_K for call in invocations)
    seen_semantic_k = False
    seen_lexical_k = False
    seen_final_top_k = False
    for call in invocations:
        if call.name == SET_SEMANTIC_K:
            if seen_lexical_k:
                _raise_order_error(
                    flow,
                    call,
                    "set_semantic_k() must appear before set_lexical_k().",
                )
            seen_semantic_k = True
            continue
        if call.name == SET_LEXICAL_K:
            if seen_final_top_k:
                _raise_order_error(
                    flow,
                    call,
                    "set_lexical_k() must appear before set_final_top_k().",
                )
            seen_lexical_k = True
            continue
        if call.name == SET_SEMANTIC_WEIGHT:
            if seen_final_top_k:
                _raise_order_error(
                    flow,
                    call,
                    "set_semantic_weight() must appear before set_final_top_k().",
                )
            continue
        if call.name == SET_FINAL_TOP_K:
            if has_semantic_k and not seen_semantic_k:
                _raise_order_error(
                    flow,
                    call,
                    "set_final_top_k() must appear after set_semantic_k().",
                )
            if has_lexical_k and not seen_lexical_k:
                _raise_order_error(
                    flow,
                    call,
                    "set_final_top_k() must appear after set_lexical_k().",
                )
            seen_final_top_k = True


def _raise_order_error(flow: ir.Flow, call: _Invocation, message: str) -> None:
    raise Namel3ssError(
        f"InvalidRetrievalParameterError: {message}",
        line=call.expr.line if call.expr.line is not None else flow.line,
        column=call.expr.column if call.expr.column is not None else flow.column,
    )


def _walk_flow_for_retrieval_calls(flow: ir.Flow) -> list[_Invocation]:
    found: list[_Invocation] = []
    for stmt in flow.body:
        found.extend(_walk_statement(flow.name, stmt))
    return found


def _walk_statement(flow_name: str, stmt: ir.Statement) -> list[_Invocation]:
    found: list[_Invocation] = []
    if isinstance(stmt, ir.Let):
        found.extend(_walk_expression(flow_name, stmt.expression))
        return found
    if isinstance(stmt, ir.Set):
        found.extend(_walk_expression(flow_name, stmt.expression))
        return found
    if isinstance(stmt, ir.If):
        found.extend(_walk_expression(flow_name, stmt.condition))
        found.extend(_walk_statements(flow_name, stmt.then_body))
        found.extend(_walk_statements(flow_name, stmt.else_body))
        return found
    if isinstance(stmt, ir.Return):
        found.extend(_walk_expression(flow_name, stmt.expression))
        return found
    if isinstance(stmt, ir.YieldStmt):
        found.extend(_walk_expression(flow_name, stmt.expression))
        return found
    if isinstance(stmt, ir.Repeat):
        found.extend(_walk_expression(flow_name, stmt.count))
        found.extend(_walk_statements(flow_name, stmt.body))
        return found
    if isinstance(stmt, ir.RepeatWhile):
        found.extend(_walk_expression(flow_name, stmt.condition))
        found.extend(_walk_statements(flow_name, stmt.body))
        return found
    if isinstance(stmt, ir.ForEach):
        found.extend(_walk_expression(flow_name, stmt.iterable))
        found.extend(_walk_statements(flow_name, stmt.body))
        return found
    if isinstance(stmt, ir.Match):
        found.extend(_walk_expression(flow_name, stmt.expression))
        for case in stmt.cases:
            found.extend(_walk_expression(flow_name, case.pattern))
            found.extend(_walk_statements(flow_name, case.body))
        found.extend(_walk_statements(flow_name, stmt.otherwise or []))
        return found
    if isinstance(stmt, ir.TryCatch):
        found.extend(_walk_statements(flow_name, stmt.try_body))
        found.extend(_walk_statements(flow_name, stmt.catch_body))
        return found
    if isinstance(stmt, ir.ParallelBlock):
        for task in stmt.tasks:
            found.extend(_walk_statements(flow_name, task.body))
        return found
    if isinstance(stmt, ir.OrchestrationBlock):
        for branch in stmt.branches:
            found.extend(_walk_expression(flow_name, branch.call_expr))
        return found
    if isinstance(stmt, ir.Find):
        found.extend(_walk_expression(flow_name, stmt.predicate))
        return found
    if isinstance(stmt, ir.LogStmt):
        found.extend(_walk_expression(flow_name, stmt.message))
        if stmt.fields is not None:
            found.extend(_walk_expression(flow_name, stmt.fields))
        return found
    if isinstance(stmt, ir.MetricStmt):
        if stmt.value is not None:
            found.extend(_walk_expression(flow_name, stmt.value))
        if stmt.labels is not None:
            found.extend(_walk_expression(flow_name, stmt.labels))
        return found
    return found


def _walk_statements(flow_name: str, statements: list[ir.Statement]) -> list[_Invocation]:
    found: list[_Invocation] = []
    for stmt in statements:
        found.extend(_walk_statement(flow_name, stmt))
    return found


def _walk_expression(flow_name: str, expr: ir.Expression) -> list[_Invocation]:
    found: list[_Invocation] = []
    if isinstance(expr, ir.AsyncCallExpr):
        found.extend(_walk_expression(flow_name, expr.expression))
        return found
    if isinstance(expr, ir.BuiltinCallExpr):
        if _looks_like_retrieval_tuning_name(expr.name):
            found.append(_Invocation(flow_name=flow_name, name=expr.name, expr=expr))
        for arg in expr.arguments:
            found.extend(_walk_expression(flow_name, arg))
        return found
    if isinstance(expr, ir.CallFunctionExpr):
        for arg in expr.arguments:
            found.extend(_walk_expression(flow_name, arg.value))
        return found
    if isinstance(expr, ir.CallFlowExpr):
        for arg in expr.arguments:
            found.extend(_walk_expression(flow_name, arg.value))
        return found
    if isinstance(expr, ir.CallPipelineExpr):
        for arg in expr.arguments:
            found.extend(_walk_expression(flow_name, arg.value))
        return found
    if isinstance(expr, ir.ToolCallExpr):
        for arg in expr.arguments:
            found.extend(_walk_expression(flow_name, arg.value))
        return found
    if isinstance(expr, ir.UnaryOp):
        found.extend(_walk_expression(flow_name, expr.operand))
        return found
    if isinstance(expr, ir.BinaryOp):
        found.extend(_walk_expression(flow_name, expr.left))
        found.extend(_walk_expression(flow_name, expr.right))
        return found
    if isinstance(expr, ir.Comparison):
        found.extend(_walk_expression(flow_name, expr.left))
        found.extend(_walk_expression(flow_name, expr.right))
        return found
    if isinstance(expr, ir.ListExpr):
        for item in expr.items:
            found.extend(_walk_expression(flow_name, item))
        return found
    if isinstance(expr, ir.MapExpr):
        for entry in expr.entries:
            found.extend(_walk_expression(flow_name, entry.key))
            found.extend(_walk_expression(flow_name, entry.value))
        return found
    if isinstance(expr, ir.ListOpExpr):
        found.extend(_walk_expression(flow_name, expr.target))
        if expr.value is not None:
            found.extend(_walk_expression(flow_name, expr.value))
        if expr.index is not None:
            found.extend(_walk_expression(flow_name, expr.index))
        return found
    if isinstance(expr, ir.ListMapExpr):
        found.extend(_walk_expression(flow_name, expr.target))
        found.extend(_walk_expression(flow_name, expr.body))
        return found
    if isinstance(expr, ir.ListFilterExpr):
        found.extend(_walk_expression(flow_name, expr.target))
        found.extend(_walk_expression(flow_name, expr.predicate))
        return found
    if isinstance(expr, ir.ListReduceExpr):
        found.extend(_walk_expression(flow_name, expr.target))
        found.extend(_walk_expression(flow_name, expr.start))
        found.extend(_walk_expression(flow_name, expr.body))
        return found
    if isinstance(expr, ir.MapOpExpr):
        found.extend(_walk_expression(flow_name, expr.target))
        if expr.key is not None:
            found.extend(_walk_expression(flow_name, expr.key))
        if expr.value is not None:
            found.extend(_walk_expression(flow_name, expr.value))
    return found


def _literal_value(expr: ir.Expression) -> tuple[bool, object]:
    if isinstance(expr, ir.Literal):
        return True, expr.value
    if isinstance(expr, ir.UnaryOp) and expr.op == "-" and isinstance(expr.operand, ir.Literal):
        value = expr.operand.value
        if isinstance(value, bool):
            return True, value
        if isinstance(value, (int, float, Decimal)):
            return True, -value
    return False, None


def _looks_like_retrieval_tuning_name(name: str) -> bool:
    if not isinstance(name, str):
        return False
    if name in set(RETRIEVAL_TUNING_FLOWS):
        return True
    return (
        name.startswith("set_semantic")
        or name.startswith("set_lexical")
        or name.startswith("set_final_top")
    )


__all__ = ["validate_retrieval_flow_usage"]
