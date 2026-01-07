from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir


def validate_parallel_task(ctx, task: ir.ParallelTask) -> None:
    for stmt in task.body:
        _validate_statement(ctx, stmt)


def ensure_tool_call_allowed(ctx, tool_name: str, *, line: int | None, column: int | None) -> None:
    if not _in_parallel(ctx):
        return
    _ensure_tool_pure(ctx, tool_name, line=line, column=column)


def ensure_ai_call_allowed(ctx, ai_name: str, *, line: int | None, column: int | None) -> None:
    if not _in_parallel(ctx):
        return
    _ensure_ai_tools_pure(ctx, ai_name, line=line, column=column)


def ensure_agent_call_allowed(ctx, agent_name: str, *, line: int | None, column: int | None) -> None:
    if not _in_parallel(ctx):
        return
    _ensure_agent_tools_pure(ctx, agent_name, line=line, column=column)


def _validate_statement(ctx, stmt: ir.Statement) -> None:
    if isinstance(stmt, ir.ParallelBlock):
        raise Namel3ssError("Nested parallel blocks are not allowed", line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.Set) and isinstance(stmt.target, ir.StatePath):
        raise Namel3ssError("Parallel tasks cannot change state", line=stmt.line, column=stmt.column)
    if isinstance(stmt, (ir.Save, ir.Create, ir.Update, ir.Delete)):
        raise Namel3ssError("Parallel tasks cannot write records", line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.ThemeChange):
        raise Namel3ssError("Parallel tasks cannot change theme", line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.AskAIStmt):
        _ensure_ai_tools_pure(ctx, stmt.ai_name, line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.RunAgentStmt):
        _ensure_agent_tools_pure(ctx, stmt.agent_name, line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.RunAgentsParallelStmt):
        for entry in stmt.entries:
            _ensure_agent_tools_pure(ctx, entry.agent_name, line=entry.line, column=entry.column)
    _scan_statement_expressions(ctx, stmt)

    if isinstance(stmt, ir.If):
        for child in stmt.then_body:
            _validate_statement(ctx, child)
        for child in stmt.else_body:
            _validate_statement(ctx, child)
        return
    if isinstance(stmt, ir.Repeat):
        for child in stmt.body:
            _validate_statement(ctx, child)
        return
    if isinstance(stmt, ir.RepeatWhile):
        for child in stmt.body:
            _validate_statement(ctx, child)
        return
    if isinstance(stmt, ir.ForEach):
        for child in stmt.body:
            _validate_statement(ctx, child)
        return
    if isinstance(stmt, ir.Match):
        for case in stmt.cases:
            for child in case.body:
                _validate_statement(ctx, child)
        if stmt.otherwise:
            for child in stmt.otherwise:
                _validate_statement(ctx, child)
        return
    if isinstance(stmt, ir.TryCatch):
        for child in stmt.try_body:
            _validate_statement(ctx, child)
        for child in stmt.catch_body:
            _validate_statement(ctx, child)
        return


def _scan_statement_expressions(ctx, stmt: ir.Statement) -> None:
    if isinstance(stmt, ir.Let):
        _scan_expression(ctx, stmt.expression)
    elif isinstance(stmt, ir.Set):
        _scan_expression(ctx, stmt.expression)
    elif isinstance(stmt, ir.Return):
        _scan_expression(ctx, stmt.expression)
    elif isinstance(stmt, ir.Repeat):
        _scan_expression(ctx, stmt.count)
    elif isinstance(stmt, ir.RepeatWhile):
        _scan_expression(ctx, stmt.condition)
    elif isinstance(stmt, ir.ForEach):
        _scan_expression(ctx, stmt.iterable)
    elif isinstance(stmt, ir.Match):
        _scan_expression(ctx, stmt.expression)
        for case in stmt.cases:
            _scan_expression(ctx, case.pattern)
    elif isinstance(stmt, ir.TryCatch):
        return
    elif isinstance(stmt, ir.AskAIStmt):
        _scan_expression(ctx, stmt.input_expr)
    elif isinstance(stmt, ir.RunAgentStmt):
        _scan_expression(ctx, stmt.input_expr)
    elif isinstance(stmt, ir.RunAgentsParallelStmt):
        for entry in stmt.entries:
            _scan_expression(ctx, entry.input_expr)
    elif isinstance(stmt, ir.Create):
        _scan_expression(ctx, stmt.values)
    elif isinstance(stmt, ir.Find):
        _scan_expression(ctx, stmt.predicate)
    elif isinstance(stmt, ir.Update):
        _scan_expression(ctx, stmt.predicate)
        for update in stmt.updates:
            _scan_expression(ctx, update.expression)
    elif isinstance(stmt, ir.Delete):
        _scan_expression(ctx, stmt.predicate)


def _scan_expression(ctx, expr: ir.Expression) -> None:
    if isinstance(expr, ir.ToolCallExpr):
        _ensure_tool_pure(ctx, expr.tool_name, line=expr.line, column=expr.column)
        for arg in expr.arguments:
            _scan_expression(ctx, arg.value)
        return
    if isinstance(expr, ir.CallFunctionExpr):
        for arg in expr.arguments:
            _scan_expression(ctx, arg.value)
        return
    if isinstance(expr, ir.UnaryOp):
        _scan_expression(ctx, expr.operand)
        return
    if isinstance(expr, ir.BinaryOp):
        _scan_expression(ctx, expr.left)
        _scan_expression(ctx, expr.right)
        return
    if isinstance(expr, ir.Comparison):
        _scan_expression(ctx, expr.left)
        _scan_expression(ctx, expr.right)
        return
    if isinstance(expr, ir.ListExpr):
        for item in expr.items:
            _scan_expression(ctx, item)
        return
    if isinstance(expr, ir.MapExpr):
        for entry in expr.entries:
            _scan_expression(ctx, entry.key)
            _scan_expression(ctx, entry.value)
        return
    if isinstance(expr, ir.ListOpExpr):
        _scan_expression(ctx, expr.target)
        if expr.value is not None:
            _scan_expression(ctx, expr.value)
        if expr.index is not None:
            _scan_expression(ctx, expr.index)
        return
    if isinstance(expr, ir.ListMapExpr):
        _scan_expression(ctx, expr.target)
        _scan_expression(ctx, expr.body)
        return
    if isinstance(expr, ir.ListFilterExpr):
        _scan_expression(ctx, expr.target)
        _scan_expression(ctx, expr.predicate)
        return
    if isinstance(expr, ir.ListReduceExpr):
        _scan_expression(ctx, expr.target)
        _scan_expression(ctx, expr.start)
        _scan_expression(ctx, expr.body)
        return
    if isinstance(expr, ir.MapOpExpr):
        _scan_expression(ctx, expr.target)
        if expr.key is not None:
            _scan_expression(ctx, expr.key)
        if expr.value is not None:
            _scan_expression(ctx, expr.value)
        return


def _in_parallel(ctx) -> bool:
    return bool(getattr(ctx, "parallel_mode", False))


def _ensure_tool_pure(ctx, tool_name: str, *, line: int | None, column: int | None) -> None:
    tool_decl = ctx.tools.get(tool_name)
    purity = getattr(tool_decl, "purity", None) if tool_decl else None
    if purity != "pure":
        raise Namel3ssError("Parallel tasks only allow pure tools", line=line, column=column)


def _ensure_ai_tools_pure(ctx, ai_name: str, *, line: int | None, column: int | None) -> None:
    profile = ctx.ai_profiles.get(ai_name)
    if profile is None:
        return
    for tool_name in profile.exposed_tools:
        _ensure_tool_pure(ctx, tool_name, line=line, column=column)


def _ensure_agent_tools_pure(ctx, agent_name: str, *, line: int | None, column: int | None) -> None:
    agent = ctx.agents.get(agent_name)
    if agent is None:
        return
    _ensure_ai_tools_pure(ctx, agent.ai_name, line=line, column=column)


__all__ = [
    "ensure_agent_call_allowed",
    "ensure_ai_call_allowed",
    "ensure_tool_call_allowed",
    "validate_parallel_task",
]
