from __future__ import annotations

from typing import Callable

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar import phase4 as sugar


def _lower_attempt_otherwise(
    stmt: sugar.AttemptOtherwiseStmt,
    lower_statements: Callable[[list[ast.Statement]], list[ast.Statement]],
) -> list[ast.Statement]:
    try_body = lower_statements(stmt.try_body)
    catch_body = lower_statements(stmt.catch_body)
    used_names = _collect_used_names(try_body + catch_body)
    catch_var = _choose_catch_var(used_names)
    return [
        ast.TryCatch(
            try_body=try_body,
            catch_var=catch_var,
            catch_body=catch_body,
            line=stmt.line,
            column=stmt.column,
        )
    ]


def _choose_catch_var(used_names: set[str]) -> str:
    if "err" not in used_names:
        return "err"
    suffix = 1
    while True:
        candidate = f"__err{suffix}"
        if candidate not in used_names:
            return candidate
        suffix += 1


def _collect_used_names(statements: list[ast.Statement]) -> set[str]:
    used: set[str] = set()
    for stmt in statements:
        _collect_from_statement(stmt, used)
    return used


def _collect_from_statement(stmt: ast.Statement, used: set[str]) -> None:
    if isinstance(stmt, ast.Let):
        used.add(stmt.name)
        _collect_from_expression(stmt.expression, used)
        return
    if isinstance(stmt, ast.Set):
        if isinstance(stmt.target, ast.VarReference):
            used.add(stmt.target.name)
        _collect_from_expression(stmt.expression, used)
        return
    if isinstance(stmt, ast.AskAIStmt):
        used.add(stmt.target)
        _collect_from_expression(stmt.input_expr, used)
        return
    if isinstance(stmt, ast.RunAgentStmt):
        used.add(stmt.target)
        _collect_from_expression(stmt.input_expr, used)
        return
    if isinstance(stmt, ast.RunAgentsParallelStmt):
        used.add(stmt.target)
        for entry in stmt.entries:
            _collect_from_expression(entry.input_expr, used)
        return
    if isinstance(stmt, ast.Create):
        used.add(stmt.target)
        _collect_from_expression(stmt.values, used)
        return
    if isinstance(stmt, ast.Find):
        _collect_from_expression(stmt.predicate, used)
        return
    if isinstance(stmt, ast.Update):
        _collect_from_expression(stmt.predicate, used)
        for update in stmt.updates:
            _collect_from_expression(update.expression, used)
        return
    if isinstance(stmt, ast.Delete):
        _collect_from_expression(stmt.predicate, used)
        return
    if isinstance(stmt, ast.If):
        _collect_from_expression(stmt.condition, used)
        for item in stmt.then_body:
            _collect_from_statement(item, used)
        for item in stmt.else_body:
            _collect_from_statement(item, used)
        return
    if isinstance(stmt, ast.Match):
        _collect_from_expression(stmt.expression, used)
        for case in stmt.cases:
            _collect_from_expression(case.pattern, used)
            for item in case.body:
                _collect_from_statement(item, used)
        if stmt.otherwise:
            for item in stmt.otherwise:
                _collect_from_statement(item, used)
        return
    if isinstance(stmt, ast.TryCatch):
        used.add(stmt.catch_var)
        for item in stmt.try_body:
            _collect_from_statement(item, used)
        for item in stmt.catch_body:
            _collect_from_statement(item, used)
        return
    if isinstance(stmt, ast.Repeat):
        _collect_from_expression(stmt.count, used)
        for item in stmt.body:
            _collect_from_statement(item, used)
        return
    if isinstance(stmt, ast.RepeatWhile):
        _collect_from_expression(stmt.condition, used)
        for item in stmt.body:
            _collect_from_statement(item, used)
        return
    if isinstance(stmt, ast.ForEach):
        used.add(stmt.name)
        _collect_from_expression(stmt.iterable, used)
        for item in stmt.body:
            _collect_from_statement(item, used)
        return
    if isinstance(stmt, ast.ParallelBlock):
        for task in stmt.tasks:
            for item in task.body:
                _collect_from_statement(item, used)
        return
    if isinstance(stmt, ast.Return):
        _collect_from_expression(stmt.expression, used)
        return


def _collect_from_expression(expr: ast.Expression | None, used: set[str]) -> None:
    if expr is None:
        return
    if isinstance(expr, ast.VarReference):
        used.add(expr.name)
        return
    if isinstance(expr, ast.AttrAccess):
        used.add(expr.base)
        return
    if isinstance(expr, ast.StatePath):
        return
    if isinstance(expr, ast.Literal):
        return
    if isinstance(expr, ast.UnaryOp):
        _collect_from_expression(expr.operand, used)
        return
    if isinstance(expr, ast.BinaryOp):
        _collect_from_expression(expr.left, used)
        _collect_from_expression(expr.right, used)
        return
    if isinstance(expr, ast.Comparison):
        _collect_from_expression(expr.left, used)
        _collect_from_expression(expr.right, used)
        return
    if isinstance(expr, ast.ToolCallExpr):
        for arg in expr.arguments:
            _collect_from_expression(arg.value, used)
        return
    if isinstance(expr, ast.CallFunctionExpr):
        for arg in expr.arguments:
            _collect_from_expression(arg.value, used)
        return
    if isinstance(expr, ast.ListExpr):
        for item in expr.items:
            _collect_from_expression(item, used)
        return
    if isinstance(expr, ast.MapExpr):
        for entry in expr.entries:
            _collect_from_expression(entry.key, used)
            _collect_from_expression(entry.value, used)
        return
    if isinstance(expr, ast.ListOpExpr):
        _collect_from_expression(expr.target, used)
        _collect_from_expression(expr.value, used)
        _collect_from_expression(expr.index, used)
        return
    if isinstance(expr, ast.MapOpExpr):
        _collect_from_expression(expr.target, used)
        _collect_from_expression(expr.key, used)
        _collect_from_expression(expr.value, used)
        return
    if isinstance(expr, ast.ListMapExpr):
        used.add(expr.var_name)
        _collect_from_expression(expr.target, used)
        _collect_from_expression(expr.body, used)
        return
    if isinstance(expr, ast.ListFilterExpr):
        used.add(expr.var_name)
        _collect_from_expression(expr.target, used)
        _collect_from_expression(expr.predicate, used)
        return
    if isinstance(expr, ast.ListReduceExpr):
        used.add(expr.acc_name)
        used.add(expr.item_name)
        _collect_from_expression(expr.target, used)
        _collect_from_expression(expr.start, used)
        _collect_from_expression(expr.body, used)
        return


__all__ = ["_lower_attempt_otherwise"]
