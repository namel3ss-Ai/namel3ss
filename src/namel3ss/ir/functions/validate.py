from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir


def validate_functions(functions: dict[str, ir.FunctionDecl]) -> None:
    for func in functions.values():
        if not _has_return(func.body):
            raise Namel3ssError(
                f'Function "{func.name}" must return a value',
                line=func.line,
                column=func.column,
            )
        _validate_function_body(func.body)
    _validate_call_graph(functions)


def _has_return(stmts: list[ir.Statement]) -> bool:
    for stmt in stmts:
        if isinstance(stmt, ir.Return):
            return True
        if isinstance(stmt, ir.If):
            if _has_return(stmt.then_body) or _has_return(stmt.else_body):
                return True
        if isinstance(stmt, ir.Repeat):
            if _has_return(stmt.body):
                return True
        if isinstance(stmt, ir.RepeatWhile):
            if _has_return(stmt.body):
                return True
        if isinstance(stmt, ir.ForEach):
            if _has_return(stmt.body):
                return True
        if isinstance(stmt, ir.Match):
            for case in stmt.cases:
                if _has_return(case.body):
                    return True
            if stmt.otherwise and _has_return(stmt.otherwise):
                return True
        if isinstance(stmt, ir.TryCatch):
            if _has_return(stmt.try_body) or _has_return(stmt.catch_body):
                return True
    return False


def _validate_function_body(stmts: list[ir.Statement]) -> None:
    for stmt in stmts:
        if isinstance(stmt, (ir.AskAIStmt, ir.RunAgentStmt, ir.RunAgentsParallelStmt)):
            raise Namel3ssError(
                "Functions cannot call ai or agents",
                line=stmt.line,
                column=stmt.column,
            )
        if isinstance(stmt, (ir.Save, ir.Create, ir.Find)):
            raise Namel3ssError(
                "Functions cannot read or write records",
                line=stmt.line,
                column=stmt.column,
            )
        if isinstance(stmt, ir.ParallelBlock):
            raise Namel3ssError(
                "Functions cannot use parallel blocks",
                line=stmt.line,
                column=stmt.column,
            )
        if isinstance(stmt, ir.Set) and isinstance(stmt.target, ir.StatePath):
            raise Namel3ssError(
                "Functions cannot change state",
                line=stmt.line,
                column=stmt.column,
            )
        if isinstance(stmt, ir.ThemeChange):
            raise Namel3ssError(
                "Functions cannot change state",
                line=stmt.line,
                column=stmt.column,
            )
        if isinstance(stmt, ir.Let):
            _validate_expression(stmt.expression)
        elif isinstance(stmt, ir.Return):
            _validate_expression(stmt.expression)
        elif isinstance(stmt, ir.If):
            _validate_expression(stmt.condition)
            _validate_function_body(stmt.then_body)
            _validate_function_body(stmt.else_body)
        elif isinstance(stmt, ir.Repeat):
            _validate_expression(stmt.count)
            _validate_function_body(stmt.body)
        elif isinstance(stmt, ir.RepeatWhile):
            _validate_expression(stmt.condition)
            _validate_function_body(stmt.body)
        elif isinstance(stmt, ir.ForEach):
            _validate_expression(stmt.iterable)
            _validate_function_body(stmt.body)
        elif isinstance(stmt, ir.Match):
            _validate_expression(stmt.expression)
            for case in stmt.cases:
                _validate_expression(case.pattern)
                _validate_function_body(case.body)
            if stmt.otherwise is not None:
                _validate_function_body(stmt.otherwise)
        elif isinstance(stmt, ir.TryCatch):
            _validate_function_body(stmt.try_body)
            _validate_function_body(stmt.catch_body)


def _validate_expression(expr: ir.Expression) -> None:
    if isinstance(expr, ir.ToolCallExpr):
        raise Namel3ssError(
            "Functions cannot call tools",
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ir.CallFunctionExpr):
        for arg in expr.arguments:
            _validate_expression(arg.value)
        return
    if isinstance(expr, ir.UnaryOp):
        _validate_expression(expr.operand)
        return
    if isinstance(expr, ir.BinaryOp):
        _validate_expression(expr.left)
        _validate_expression(expr.right)
        return
    if isinstance(expr, ir.Comparison):
        _validate_expression(expr.left)
        _validate_expression(expr.right)
        return
    if isinstance(expr, ir.ListExpr):
        for item in expr.items:
            _validate_expression(item)
        return
    if isinstance(expr, ir.MapExpr):
        for entry in expr.entries:
            _validate_expression(entry.key)
            _validate_expression(entry.value)
        return
    if isinstance(expr, ir.ListOpExpr):
        _validate_expression(expr.target)
        if expr.value is not None:
            _validate_expression(expr.value)
        if expr.index is not None:
            _validate_expression(expr.index)
        return
    if isinstance(expr, ir.ListMapExpr):
        _validate_expression(expr.target)
        _validate_expression(expr.body)
        return
    if isinstance(expr, ir.ListFilterExpr):
        _validate_expression(expr.target)
        _validate_expression(expr.predicate)
        return
    if isinstance(expr, ir.ListReduceExpr):
        _validate_expression(expr.target)
        _validate_expression(expr.start)
        _validate_expression(expr.body)
        return
    if isinstance(expr, ir.MapOpExpr):
        _validate_expression(expr.target)
        if expr.key is not None:
            _validate_expression(expr.key)
        if expr.value is not None:
            _validate_expression(expr.value)
        return


def _validate_call_graph(functions: dict[str, ir.FunctionDecl]) -> None:
    call_graph = {name: _collect_calls(func.body) for name, func in functions.items()}
    for func_name, calls in call_graph.items():
        for target in calls:
            if target not in functions:
                raise Namel3ssError(
                    f'Unknown function "{target}"',
                    line=functions[func_name].line,
                    column=functions[func_name].column,
                )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise Namel3ssError(
                "Function recursion is not allowed",
                line=functions[name].line,
                column=functions[name].column,
            )
        if name in visited:
            return
        visiting.add(name)
        for target in call_graph.get(name, set()):
            visit(target)
        visiting.remove(name)
        visited.add(name)

    for name in functions:
        visit(name)


def _collect_calls(stmts: list[ir.Statement]) -> set[str]:
    calls: set[str] = set()
    for stmt in stmts:
        if isinstance(stmt, ir.Let):
            calls.update(_collect_calls_from_expr(stmt.expression))
        elif isinstance(stmt, ir.Return):
            calls.update(_collect_calls_from_expr(stmt.expression))
        elif isinstance(stmt, ir.If):
            calls.update(_collect_calls_from_expr(stmt.condition))
            calls.update(_collect_calls(stmt.then_body))
            calls.update(_collect_calls(stmt.else_body))
        elif isinstance(stmt, ir.Repeat):
            calls.update(_collect_calls_from_expr(stmt.count))
            calls.update(_collect_calls(stmt.body))
        elif isinstance(stmt, ir.RepeatWhile):
            calls.update(_collect_calls_from_expr(stmt.condition))
            calls.update(_collect_calls(stmt.body))
        elif isinstance(stmt, ir.ForEach):
            calls.update(_collect_calls_from_expr(stmt.iterable))
            calls.update(_collect_calls(stmt.body))
        elif isinstance(stmt, ir.Match):
            calls.update(_collect_calls_from_expr(stmt.expression))
            for case in stmt.cases:
                calls.update(_collect_calls_from_expr(case.pattern))
                calls.update(_collect_calls(case.body))
            if stmt.otherwise is not None:
                calls.update(_collect_calls(stmt.otherwise))
        elif isinstance(stmt, ir.TryCatch):
            calls.update(_collect_calls(stmt.try_body))
            calls.update(_collect_calls(stmt.catch_body))
    return calls


def _collect_calls_from_expr(expr: ir.Expression) -> set[str]:
    calls: set[str] = set()
    if isinstance(expr, ir.CallFunctionExpr):
        calls.add(expr.function_name)
        for arg in expr.arguments:
            calls.update(_collect_calls_from_expr(arg.value))
        return calls
    if isinstance(expr, ir.UnaryOp):
        return _collect_calls_from_expr(expr.operand)
    if isinstance(expr, ir.BinaryOp):
        calls.update(_collect_calls_from_expr(expr.left))
        calls.update(_collect_calls_from_expr(expr.right))
        return calls
    if isinstance(expr, ir.Comparison):
        calls.update(_collect_calls_from_expr(expr.left))
        calls.update(_collect_calls_from_expr(expr.right))
        return calls
    if isinstance(expr, ir.ListExpr):
        for item in expr.items:
            calls.update(_collect_calls_from_expr(item))
        return calls
    if isinstance(expr, ir.MapExpr):
        for entry in expr.entries:
            calls.update(_collect_calls_from_expr(entry.key))
            calls.update(_collect_calls_from_expr(entry.value))
        return calls
    if isinstance(expr, ir.ListOpExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        if expr.value is not None:
            calls.update(_collect_calls_from_expr(expr.value))
        if expr.index is not None:
            calls.update(_collect_calls_from_expr(expr.index))
        return calls
    if isinstance(expr, ir.ListMapExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        calls.update(_collect_calls_from_expr(expr.body))
        return calls
    if isinstance(expr, ir.ListFilterExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        calls.update(_collect_calls_from_expr(expr.predicate))
        return calls
    if isinstance(expr, ir.ListReduceExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        calls.update(_collect_calls_from_expr(expr.start))
        calls.update(_collect_calls_from_expr(expr.body))
        return calls
    if isinstance(expr, ir.MapOpExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        if expr.key is not None:
            calls.update(_collect_calls_from_expr(expr.key))
        if expr.value is not None:
            calls.update(_collect_calls_from_expr(expr.value))
        return calls
    return calls


__all__ = ["validate_functions"]
