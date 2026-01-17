from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.lowering.statements import _lower_statement


def lower_jobs(jobs: list[ast.JobDecl], agents: dict[str, ir.AgentDecl]) -> list[ir.JobDecl]:
    lowered: list[ir.JobDecl] = []
    seen: dict[str, ast.JobDecl] = {}
    for job in jobs:
        if job.name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Job '{job.name}' is declared more than once.",
                    why="Jobs must have unique names.",
                    fix="Rename the duplicate job or remove it.",
                    example='job "refresh cache":\n  return "ok"',
                ),
                line=job.line,
                column=job.column,
            )
        seen[job.name] = job
        body = [_lower_statement(stmt, agents) for stmt in job.body]
        when_expr = _lower_expression(job.when) if job.when else None
        if when_expr is not None:
            _ensure_no_tool_calls(when_expr, job)
        lowered.append(
            ir.JobDecl(
                name=job.name,
                body=body,
                when=when_expr,
                line=job.line,
                column=job.column,
            )
        )
    return lowered


def _ensure_no_tool_calls(expr: ir.Expression, job: ast.JobDecl) -> None:
    if isinstance(expr, ir.ToolCallExpr):
        raise Namel3ssError(
            "Job when clauses cannot call tools",
            line=job.line,
            column=job.column,
        )
    if isinstance(expr, ir.CallFunctionExpr):
        for arg in expr.arguments:
            _ensure_no_tool_calls(arg.value, job)
        return
    if isinstance(expr, ir.UnaryOp):
        _ensure_no_tool_calls(expr.operand, job)
        return
    if isinstance(expr, ir.BinaryOp):
        _ensure_no_tool_calls(expr.left, job)
        _ensure_no_tool_calls(expr.right, job)
        return
    if isinstance(expr, ir.Comparison):
        _ensure_no_tool_calls(expr.left, job)
        _ensure_no_tool_calls(expr.right, job)
        return
    if isinstance(expr, ir.ListExpr):
        for item in expr.items:
            _ensure_no_tool_calls(item, job)
        return
    if isinstance(expr, ir.MapExpr):
        for entry in expr.entries:
            _ensure_no_tool_calls(entry.key, job)
            _ensure_no_tool_calls(entry.value, job)
        return
    if isinstance(expr, ir.ListOpExpr):
        _ensure_no_tool_calls(expr.target, job)
        if expr.value is not None:
            _ensure_no_tool_calls(expr.value, job)
        if expr.index is not None:
            _ensure_no_tool_calls(expr.index, job)
        return
    if isinstance(expr, ir.MapOpExpr):
        _ensure_no_tool_calls(expr.target, job)
        if expr.key is not None:
            _ensure_no_tool_calls(expr.key, job)
        if expr.value is not None:
            _ensure_no_tool_calls(expr.value, job)
        return
    if isinstance(expr, ir.ListMapExpr):
        _ensure_no_tool_calls(expr.target, job)
        _ensure_no_tool_calls(expr.body, job)
        return
    if isinstance(expr, ir.ListFilterExpr):
        _ensure_no_tool_calls(expr.target, job)
        _ensure_no_tool_calls(expr.predicate, job)
        return
    if isinstance(expr, ir.ListReduceExpr):
        _ensure_no_tool_calls(expr.target, job)
        _ensure_no_tool_calls(expr.start, job)
        _ensure_no_tool_calls(expr.body, job)
        return
