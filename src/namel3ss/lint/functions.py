from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.lint.types import Finding
from namel3ss.utils.numbers import is_number


def lint_functions(program: ast.Program) -> list[Finding]:
    findings: list[Finding] = []
    functions = {func.name: func for func in getattr(program, "functions", [])}
    for func in functions.values():
        if not _has_return(func.body):
            findings.append(
                Finding(
                    code="functions.missing_return",
                    message="Function must return a value",
                    line=func.line,
                    column=func.column,
                )
            )
        findings.extend(_lint_function_body(func.body))
    findings.extend(_lint_function_calls(functions))
    return findings


def _has_return(stmts: list[ast.Statement]) -> bool:
    for stmt in stmts:
        if isinstance(stmt, ast.Return):
            return True
        if isinstance(stmt, ast.If):
            if _has_return(stmt.then_body) or _has_return(stmt.else_body):
                return True
        if isinstance(stmt, ast.Repeat):
            if _has_return(stmt.body):
                return True
        if isinstance(stmt, ast.RepeatWhile):
            if _has_return(stmt.body):
                return True
        if isinstance(stmt, ast.ForEach):
            if _has_return(stmt.body):
                return True
        if isinstance(stmt, ast.Match):
            for case in stmt.cases:
                if _has_return(case.body):
                    return True
            if stmt.otherwise and _has_return(stmt.otherwise):
                return True
        if isinstance(stmt, ast.TryCatch):
            if _has_return(stmt.try_body) or _has_return(stmt.catch_body):
                return True
    return False


def _lint_function_body(stmts: list[ast.Statement]) -> list[Finding]:
    findings: list[Finding] = []
    for stmt in stmts:
        if isinstance(stmt, (ast.AskAIStmt, ast.RunAgentStmt, ast.RunAgentsParallelStmt)):
            findings.append(
                Finding(
                    code="functions.ai_not_allowed",
                    message="Function cannot call ai or agents",
                    line=stmt.line,
                    column=stmt.column,
                )
            )
        if isinstance(stmt, (ast.Save, ast.Create, ast.Find)):
            findings.append(
                Finding(
                    code="functions.records_not_allowed",
                    message="Function cannot read or write records",
                    line=stmt.line,
                    column=stmt.column,
                )
            )
        if isinstance(stmt, ast.Set) and isinstance(stmt.target, ast.StatePath):
            findings.append(
                Finding(
                    code="functions.state_not_allowed",
                    message="Function cannot change state",
                    line=stmt.line,
                    column=stmt.column,
                )
            )
        if isinstance(stmt, ast.ThemeChange):
            findings.append(
                Finding(
                    code="functions.state_not_allowed",
                    message="Function cannot change state",
                    line=stmt.line,
                    column=stmt.column,
                )
            )
        if isinstance(stmt, ast.RepeatWhile):
            if stmt.limit <= 0:
                findings.append(
                    Finding(
                        code="loops.limit_invalid",
                        message="Loop limit must be greater than zero",
                        line=stmt.limit_line or stmt.line,
                        column=stmt.limit_column or stmt.column,
                    )
                )
        findings.extend(_lint_expression(getattr(stmt, "expression", None)))
        findings.extend(_lint_expression(getattr(stmt, "condition", None)))
        findings.extend(_lint_expression(getattr(stmt, "iterable", None)))
        findings.extend(_lint_expression(getattr(stmt, "count", None)))
        if isinstance(stmt, ast.Match):
            for case in stmt.cases:
                findings.extend(_lint_expression(case.pattern))
        if isinstance(stmt, ast.Create):
            findings.extend(_lint_expression(stmt.values))
        if isinstance(stmt, ast.Find):
            findings.extend(_lint_expression(stmt.predicate))
        if hasattr(stmt, "body"):
            findings.extend(_lint_function_body(getattr(stmt, "body")))
        if hasattr(stmt, "then_body"):
            findings.extend(_lint_function_body(stmt.then_body))
        if hasattr(stmt, "else_body"):
            findings.extend(_lint_function_body(stmt.else_body))
        if hasattr(stmt, "try_body"):
            findings.extend(_lint_function_body(stmt.try_body))
        if hasattr(stmt, "catch_body"):
            findings.extend(_lint_function_body(stmt.catch_body))
        if hasattr(stmt, "cases"):
            for case in stmt.cases:
                findings.extend(_lint_function_body(case.body))
        if hasattr(stmt, "otherwise") and stmt.otherwise:
            findings.extend(_lint_function_body(stmt.otherwise))
    return findings


def _lint_function_calls(functions: dict[str, ast.FunctionDecl]) -> list[Finding]:
    findings: list[Finding] = []
    call_graph = {name: _collect_calls(func.body) for name, func in functions.items()}
    for name, calls in call_graph.items():
        for target in calls:
            if target not in functions:
                findings.append(
                    Finding(
                        code="functions.unknown_call",
                        message=f"Unknown function '{target}'",
                        line=functions[name].line,
                        column=functions[name].column,
                    )
                )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            findings.append(
                Finding(
                    code="functions.recursion",
                    message="Function recursion is not allowed",
                    line=functions[name].line,
                    column=functions[name].column,
                )
            )
            return
        if name in visited:
            return
        visiting.add(name)
        for target in call_graph.get(name, set()):
            visit(target)
        visiting.remove(name)
        visited.add(name)

    for name in functions:
        visit(name)
    return findings


def _collect_calls(stmts: list[ast.Statement]) -> set[str]:
    calls: set[str] = set()
    for stmt in stmts:
        calls.update(_collect_calls_from_expr(getattr(stmt, "expression", None)))
        calls.update(_collect_calls_from_expr(getattr(stmt, "condition", None)))
        calls.update(_collect_calls_from_expr(getattr(stmt, "iterable", None)))
        calls.update(_collect_calls_from_expr(getattr(stmt, "count", None)))
        if isinstance(stmt, ast.Match):
            for case in stmt.cases:
                calls.update(_collect_calls_from_expr(case.pattern))
        if isinstance(stmt, ast.Create):
            calls.update(_collect_calls_from_expr(stmt.values))
        if isinstance(stmt, ast.Find):
            calls.update(_collect_calls_from_expr(stmt.predicate))
        if hasattr(stmt, "body"):
            calls.update(_collect_calls(getattr(stmt, "body")))
        if hasattr(stmt, "then_body"):
            calls.update(_collect_calls(stmt.then_body))
        if hasattr(stmt, "else_body"):
            calls.update(_collect_calls(stmt.else_body))
        if hasattr(stmt, "try_body"):
            calls.update(_collect_calls(stmt.try_body))
        if hasattr(stmt, "catch_body"):
            calls.update(_collect_calls(stmt.catch_body))
        if hasattr(stmt, "cases"):
            for case in stmt.cases:
                calls.update(_collect_calls(case.body))
        if hasattr(stmt, "otherwise") and stmt.otherwise:
            calls.update(_collect_calls(stmt.otherwise))
    return calls


def _collect_calls_from_expr(expr: ast.Expression | None) -> set[str]:
    calls: set[str] = set()
    if expr is None:
        return calls
    if isinstance(expr, ast.CallFunctionExpr):
        calls.add(expr.function_name)
        for arg in expr.arguments:
            calls.update(_collect_calls_from_expr(arg.value))
        return calls
    if isinstance(expr, ast.UnaryOp):
        return _collect_calls_from_expr(expr.operand)
    if isinstance(expr, ast.BinaryOp):
        calls.update(_collect_calls_from_expr(expr.left))
        calls.update(_collect_calls_from_expr(expr.right))
        return calls
    if isinstance(expr, ast.Comparison):
        calls.update(_collect_calls_from_expr(expr.left))
        calls.update(_collect_calls_from_expr(expr.right))
        return calls
    if isinstance(expr, ast.ListExpr):
        for item in expr.items:
            calls.update(_collect_calls_from_expr(item))
        return calls
    if isinstance(expr, ast.MapExpr):
        for entry in expr.entries:
            calls.update(_collect_calls_from_expr(entry.key))
            calls.update(_collect_calls_from_expr(entry.value))
        return calls
    if isinstance(expr, ast.ListMapExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        calls.update(_collect_calls_from_expr(expr.body))
        return calls
    if isinstance(expr, ast.ListFilterExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        calls.update(_collect_calls_from_expr(expr.predicate))
        return calls
    if isinstance(expr, ast.ListReduceExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        calls.update(_collect_calls_from_expr(expr.start))
        calls.update(_collect_calls_from_expr(expr.body))
        return calls
    if isinstance(expr, ast.ListOpExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        calls.update(_collect_calls_from_expr(expr.value))
        calls.update(_collect_calls_from_expr(expr.index))
        return calls
    if isinstance(expr, ast.MapOpExpr):
        calls.update(_collect_calls_from_expr(expr.target))
        calls.update(_collect_calls_from_expr(expr.key))
        calls.update(_collect_calls_from_expr(expr.value))
        return calls
    return calls


def _lint_expression(expr: ast.Expression | None) -> list[Finding]:
    if expr is None:
        return []
    findings: list[Finding] = []
    findings.extend(_lint_operator_expr(expr))
    if isinstance(expr, ast.ToolCallExpr):
        findings.append(
            Finding(
                code="functions.tool_not_allowed",
                message="Function cannot call tools",
                line=expr.line,
                column=expr.column,
            )
        )
    if isinstance(expr, ast.UnaryOp):
        findings.extend(_lint_expression(expr.operand))
    if isinstance(expr, ast.BinaryOp):
        findings.extend(_lint_expression(expr.left))
        findings.extend(_lint_expression(expr.right))
    if isinstance(expr, ast.Comparison):
        findings.extend(_lint_expression(expr.left))
        findings.extend(_lint_expression(expr.right))
    if isinstance(expr, ast.ListExpr):
        for item in expr.items:
            findings.extend(_lint_expression(item))
    if isinstance(expr, ast.MapExpr):
        for entry in expr.entries:
            findings.extend(_lint_expression(entry.key))
            findings.extend(_lint_expression(entry.value))
    if isinstance(expr, ast.ListOpExpr):
        findings.extend(_lint_expression(expr.target))
        findings.extend(_lint_expression(expr.value))
        findings.extend(_lint_expression(expr.index))
    if isinstance(expr, ast.MapOpExpr):
        findings.extend(_lint_expression(expr.target))
        findings.extend(_lint_expression(expr.key))
        findings.extend(_lint_expression(expr.value))
    if isinstance(expr, ast.CallFunctionExpr):
        for arg in expr.arguments:
            findings.extend(_lint_expression(arg.value))
    return findings


def _lint_operator_expr(expr: ast.Expression) -> list[Finding]:
    findings: list[Finding] = []
    if isinstance(expr, ast.UnaryOp):
        operand_type = _literal_type(expr.operand)
        if expr.op in {"+", "-"} and operand_type and operand_type != "number":
            findings.append(
                Finding(
                    code="operators.invalid_unary",
                    message="Unary operator needs a number",
                    line=expr.line,
                    column=expr.column,
                )
            )
        if expr.op == "not" and operand_type and operand_type != "boolean":
            findings.append(
                Finding(
                    code="operators.invalid_not",
                    message="Not needs a boolean",
                    line=expr.line,
                    column=expr.column,
                )
            )
    if isinstance(expr, ast.BinaryOp):
        left_type = _literal_type(expr.left)
        right_type = _literal_type(expr.right)
        if expr.op in {"+", "-", "*", "/", "%"}:
            if (left_type and left_type != "number") or (right_type and right_type != "number"):
                findings.append(
                    Finding(
                        code="operators.invalid_math",
                        message="Math operators need numbers",
                        line=expr.line,
                        column=expr.column,
                    )
                )
        if expr.op in {"and", "or"}:
            if (left_type and left_type != "boolean") or (right_type and right_type != "boolean"):
                findings.append(
                    Finding(
                        code="operators.invalid_bool",
                        message="Boolean operators need true or false",
                        line=expr.line,
                        column=expr.column,
                    )
                )
    if isinstance(expr, ast.Comparison):
        left_type = _literal_type(expr.left)
        right_type = _literal_type(expr.right)
        if expr.kind in {"gt", "lt", "gte", "lte"}:
            if (left_type and left_type != "number") or (right_type and right_type != "number"):
                findings.append(
                    Finding(
                        code="operators.invalid_compare",
                        message="Comparison needs numbers",
                        line=expr.line,
                        column=expr.column,
                    )
                )
    return findings


def _literal_type(expr: ast.Expression) -> str | None:
    if isinstance(expr, ast.Literal):
        if isinstance(expr.value, bool):
            return "boolean"
        if is_number(expr.value):
            return "number"
        if isinstance(expr.value, str):
            return "text"
        return None
    if isinstance(expr, ast.ListExpr):
        return "list"
    if isinstance(expr, ast.MapExpr):
        return "map"
    return None


__all__ = ["lint_functions"]
