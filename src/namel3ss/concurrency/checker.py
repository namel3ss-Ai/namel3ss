from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast import nodes as ast
from namel3ss.parser.core import parse


@dataclass(frozen=True)
class ConcurrencyViolation:
    flow_name: str
    line: int
    column: int
    reason: str
    suggestion: str

    def to_dict(self) -> dict[str, object]:
        return {
            "flow_name": self.flow_name,
            "line": int(self.line),
            "column": int(self.column),
            "reason": self.reason,
            "suggestion": self.suggestion,
        }


def run_concurrency_checks(source: str) -> dict[str, object]:
    program = parse(source)
    violations: list[ConcurrencyViolation] = []
    for flow in getattr(program, "flows", []):
        launched: set[str] = set()
        violations.extend(_scan_statements(flow.name, flow.body, launched=launched, in_parallel=False))
    rows = [item.to_dict() for item in _sorted_violations(violations)]
    return {
        "ok": len(rows) == 0,
        "count": len(rows),
        "violations": rows,
    }


def _scan_statements(
    flow_name: str,
    statements: list[ast.Statement],
    *,
    launched: set[str],
    in_parallel: bool,
) -> list[ConcurrencyViolation]:
    violations: list[ConcurrencyViolation] = []
    local_launched = set(launched)
    for stmt in statements:
        if isinstance(stmt, ast.Let) and isinstance(stmt.expression, ast.AsyncCallExpr):
            if not _is_call_expression(stmt.expression.expression):
                violations.append(
                    _violation(
                        flow_name,
                        stmt.line,
                        stmt.column,
                        "async can only launch a call.",
                        "Use async with a tool call, function call, flow call, or pipeline call.",
                    )
                )
            local_launched.add(stmt.name)
            continue
        if isinstance(stmt, ast.Await):
            if stmt.name not in local_launched:
                violations.append(
                    _violation(
                        flow_name,
                        stmt.line,
                        stmt.column,
                        f"await '{stmt.name}' has no matching async launch.",
                        "Launch it first with `let name is async ...`.",
                    )
                )
            continue
        if isinstance(stmt, ast.ParallelBlock):
            for task in stmt.tasks:
                violations.extend(
                    _scan_parallel_task(
                        flow_name,
                        task,
                    )
                )
            continue
        if in_parallel and isinstance(stmt, ast.Set) and isinstance(stmt.target, ast.StatePath):
            violations.append(
                _violation(
                    flow_name,
                    stmt.line,
                    stmt.column,
                    "parallel block changes shared state.",
                    "Move state writes out of parallel, or write local values and merge after.",
                )
            )
        if in_parallel and isinstance(stmt, (ast.Save, ast.Create, ast.Update, ast.Delete, ast.ThemeChange)):
            violations.append(
                _violation(
                    flow_name,
                    stmt.line,
                    stmt.column,
                    "parallel block runs a shared side effect.",
                    "Keep side effects outside parallel and only compute values in parallel.",
                )
            )

        if isinstance(stmt, ast.If):
            then_launched = set(local_launched)
            else_launched = set(local_launched)
            violations.extend(_scan_statements(flow_name, stmt.then_body, launched=then_launched, in_parallel=in_parallel))
            violations.extend(_scan_statements(flow_name, stmt.else_body, launched=else_launched, in_parallel=in_parallel))
            local_launched = then_launched | else_launched
            continue
        if isinstance(stmt, ast.Repeat):
            body_launched = set(local_launched)
            violations.extend(_scan_statements(flow_name, stmt.body, launched=body_launched, in_parallel=in_parallel))
            local_launched |= body_launched
            continue
        if isinstance(stmt, ast.RepeatWhile):
            body_launched = set(local_launched)
            violations.extend(_scan_statements(flow_name, stmt.body, launched=body_launched, in_parallel=in_parallel))
            local_launched |= body_launched
            continue
        if isinstance(stmt, ast.ForEach):
            body_launched = set(local_launched)
            violations.extend(_scan_statements(flow_name, stmt.body, launched=body_launched, in_parallel=in_parallel))
            local_launched |= body_launched
            continue
        if isinstance(stmt, ast.Match):
            for case in stmt.cases:
                case_launched = set(local_launched)
                violations.extend(_scan_statements(flow_name, case.body, launched=case_launched, in_parallel=in_parallel))
                local_launched |= case_launched
            if stmt.otherwise:
                other_launched = set(local_launched)
                violations.extend(
                    _scan_statements(flow_name, stmt.otherwise, launched=other_launched, in_parallel=in_parallel)
                )
                local_launched |= other_launched
            continue
        if isinstance(stmt, ast.TryCatch):
            try_launched = set(local_launched)
            catch_launched = set(local_launched)
            violations.extend(_scan_statements(flow_name, stmt.try_body, launched=try_launched, in_parallel=in_parallel))
            violations.extend(_scan_statements(flow_name, stmt.catch_body, launched=catch_launched, in_parallel=in_parallel))
            local_launched = try_launched | catch_launched
            continue

    launched.clear()
    launched.update(local_launched)
    return violations


def _scan_parallel_task(flow_name: str, task: ast.ParallelTask) -> list[ConcurrencyViolation]:
    launched: set[str] = set()
    return _scan_statements(flow_name, task.body, launched=launched, in_parallel=True)


def _is_call_expression(expr: ast.Expression) -> bool:
    return isinstance(expr, (ast.ToolCallExpr, ast.CallFunctionExpr, ast.CallFlowExpr, ast.CallPipelineExpr))


def _violation(flow_name: str, line: int | None, column: int | None, reason: str, suggestion: str) -> ConcurrencyViolation:
    return ConcurrencyViolation(
        flow_name=flow_name,
        line=int(line or 0),
        column=int(column or 0),
        reason=reason,
        suggestion=suggestion,
    )


def _sorted_violations(items: list[ConcurrencyViolation]) -> list[ConcurrencyViolation]:
    return sorted(
        items,
        key=lambda item: (item.flow_name, item.line, item.column, item.reason),
    )


__all__ = ["ConcurrencyViolation", "run_concurrency_checks"]
