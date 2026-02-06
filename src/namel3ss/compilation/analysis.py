from __future__ import annotations

from decimal import Decimal

from namel3ss.compilation.model import (
    BinaryNumber,
    InputNumber,
    LocalNumber,
    NumberLiteral,
    NumericAssignment,
    NumericExpr,
    NumericFlowPlan,
    UnaryNumber,
)
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.utils.numbers import decimal_to_str


_ALLOWED_BINARY_OPS = {"+", "-", "*", "/", "%"}
_ALLOWED_UNARY_OPS = {"+", "-"}


def build_numeric_flow_plan(program: ir.Program, flow_name: str) -> NumericFlowPlan:
    flow = _resolve_flow(program, flow_name)
    if getattr(flow, "purity", "effectful") != "pure":
        raise Namel3ssError(_flow_not_pure_message(flow.name), line=flow.line, column=flow.column)
    if getattr(flow, "requires", None) is not None:
        raise Namel3ssError(_unsupported_requires_message(flow.name), line=flow.line, column=flow.column)
    if getattr(flow, "audited", False):
        raise Namel3ssError(_unsupported_flow_mode_message(flow.name, "audited"), line=flow.line, column=flow.column)
    if getattr(flow, "declarative", False):
        raise Namel3ssError(_unsupported_flow_mode_message(flow.name, "declarative"), line=flow.line, column=flow.column)

    assignments: list[NumericAssignment] = []
    input_keys: list[str] = []
    seen_inputs: set[str] = set()
    locals_seen: set[str] = set()
    result_expr: NumericExpr | None = None
    return_seen = False

    for stmt in flow.body:
        if isinstance(stmt, ir.Let):
            if return_seen:
                raise Namel3ssError(_unsupported_statement_after_return_message(flow.name), line=stmt.line, column=stmt.column)
            expr = _to_numeric_expr(stmt.expression, locals_seen=locals_seen, seen_inputs=seen_inputs, input_keys=input_keys)
            locals_seen.add(stmt.name)
            assignments.append(NumericAssignment(name=stmt.name, expr=expr))
            continue
        if isinstance(stmt, ir.Return):
            if return_seen:
                raise Namel3ssError(_unsupported_statement_after_return_message(flow.name), line=stmt.line, column=stmt.column)
            result_expr = _to_numeric_expr(stmt.expression, locals_seen=locals_seen, seen_inputs=seen_inputs, input_keys=input_keys)
            return_seen = True
            continue
        raise Namel3ssError(
            _unsupported_statement_message(flow.name, stmt.__class__.__name__),
            line=getattr(stmt, "line", flow.line),
            column=getattr(stmt, "column", flow.column),
        )

    if result_expr is None:
        raise Namel3ssError(_missing_return_message(flow.name), line=flow.line, column=flow.column)

    return NumericFlowPlan(
        flow_name=flow.name,
        assignments=tuple(assignments),
        result=result_expr,
        input_keys=tuple(input_keys),
    )


def _resolve_flow(program: ir.Program, flow_name: str) -> ir.Flow:
    for flow in getattr(program, "flows", []) or []:
        if flow.name == flow_name:
            return flow
    raise Namel3ssError(_unknown_flow_message(flow_name, tuple(flow.name for flow in getattr(program, "flows", []) or [])))


def _to_numeric_expr(
    expr: ir.Expression,
    *,
    locals_seen: set[str],
    seen_inputs: set[str],
    input_keys: list[str],
) -> NumericExpr:
    if isinstance(expr, ir.Literal):
        text = _literal_to_number(expr.value)
        return NumberLiteral(text=text)
    if isinstance(expr, ir.VarReference):
        if expr.name not in locals_seen:
            raise Namel3ssError(
                _unknown_local_message(expr.name),
                line=getattr(expr, "line", None),
                column=getattr(expr, "column", None),
            )
        return LocalNumber(name=expr.name)
    if isinstance(expr, ir.AttrAccess):
        if expr.base != "input":
            raise Namel3ssError(
                _unsupported_expression_message("AttrAccess base must be input"),
                line=getattr(expr, "line", None),
                column=getattr(expr, "column", None),
            )
        if len(expr.attrs) != 1:
            raise Namel3ssError(
                _unsupported_expression_message("Only one input field level is supported"),
                line=getattr(expr, "line", None),
                column=getattr(expr, "column", None),
            )
        key = str(expr.attrs[0])
        if key not in seen_inputs:
            seen_inputs.add(key)
            input_keys.append(key)
        return InputNumber(key=key)
    if isinstance(expr, ir.UnaryOp):
        if expr.op not in _ALLOWED_UNARY_OPS:
            raise Namel3ssError(
                _unsupported_expression_message(f"Unary operator '{expr.op}' is not supported"),
                line=getattr(expr, "line", None),
                column=getattr(expr, "column", None),
            )
        operand = _to_numeric_expr(expr.operand, locals_seen=locals_seen, seen_inputs=seen_inputs, input_keys=input_keys)
        return UnaryNumber(op=expr.op, operand=operand)
    if isinstance(expr, ir.BinaryOp):
        if expr.op not in _ALLOWED_BINARY_OPS:
            raise Namel3ssError(
                _unsupported_expression_message(f"Binary operator '{expr.op}' is not supported"),
                line=getattr(expr, "line", None),
                column=getattr(expr, "column", None),
            )
        left = _to_numeric_expr(expr.left, locals_seen=locals_seen, seen_inputs=seen_inputs, input_keys=input_keys)
        right = _to_numeric_expr(expr.right, locals_seen=locals_seen, seen_inputs=seen_inputs, input_keys=input_keys)
        return BinaryNumber(op=expr.op, left=left, right=right)
    raise Namel3ssError(
        _unsupported_expression_message(expr.__class__.__name__),
        line=getattr(expr, "line", None),
        column=getattr(expr, "column", None),
    )


def _literal_to_number(value: object) -> str:
    if isinstance(value, Decimal):
        return decimal_to_str(value)
    if isinstance(value, bool):
        raise Namel3ssError(_unsupported_expression_message("Boolean literals are not supported in compiled numeric flows"))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    raise Namel3ssError(_unsupported_expression_message("Only numeric literals are supported"))


def _unknown_flow_message(name: str, available: tuple[str, ...]) -> str:
    sample = ", ".join(sorted(available)[:5]) if available else "none"
    return build_guidance_message(
        what=f"Unknown flow '{name}'.",
        why=f"Available flows: {sample}.",
        fix="Use a flow defined in app.ai.",
        example="n3 compile --lang rust --flow demo",
    )


def _flow_not_pure_message(name: str) -> str:
    return build_guidance_message(
        what=f"Flow '{name}' cannot be compiled.",
        why="Cross-language compilation in this phase supports pure flows only.",
        fix='Declare the flow as purity is "pure" and remove side effects.',
        example='flow "demo": purity is "pure"',
    )


def _unsupported_requires_message(name: str) -> str:
    return build_guidance_message(
        what=f"Flow '{name}' cannot be compiled.",
        why="Compiled flows do not evaluate requires expressions in this phase.",
        fix="Remove the requires guard or run the flow in Python runtime.",
        example='flow "demo": purity is "pure"',
    )


def _unsupported_flow_mode_message(name: str, mode: str) -> str:
    return build_guidance_message(
        what=f"Flow '{name}' cannot be compiled.",
        why=f"Compiled flows do not support {mode} mode in this phase.",
        fix="Use a non-compiled execution target for this flow.",
        example="n3 run app.ai",
    )


def _unsupported_statement_message(flow_name: str, statement_name: str) -> str:
    return build_guidance_message(
        what=f"Flow '{flow_name}' uses unsupported statement '{statement_name}'.",
        why="Compiled numeric flows support let and return statements only.",
        fix="Simplify the flow or keep it on Python runtime.",
        example='flow "demo": purity is "pure"\n  let x is input.a + 1\n  return x',
    )


def _unsupported_statement_after_return_message(flow_name: str) -> str:
    return build_guidance_message(
        what=f"Flow '{flow_name}' has statements after return.",
        why="Compiled numeric flow generation needs a single return path.",
        fix="Move return to the end of the flow.",
        example='flow "demo": purity is "pure"\n  let x is 1\n  return x',
    )


def _missing_return_message(flow_name: str) -> str:
    return build_guidance_message(
        what=f"Flow '{flow_name}' has no return.",
        why="Compiled numeric flows require a return value.",
        fix="Add a return statement.",
        example='flow "demo": purity is "pure"\n  return 1',
    )


def _unknown_local_message(name: str) -> str:
    return build_guidance_message(
        what=f"Unknown local '{name}' in compiled flow.",
        why="Compiled flow references must be declared earlier with let.",
        fix="Declare the local before use.",
        example='let total is input.a + input.b',
    )


def _unsupported_expression_message(detail: str) -> str:
    return build_guidance_message(
        what="Expression is not supported for cross-language compilation.",
        why=detail,
        fix="Use numeric literals, input.<field>, local refs, and + - * / % operators.",
        example='let total is input.a + input.b',
    )


__all__ = ["build_numeric_flow_plan"]
