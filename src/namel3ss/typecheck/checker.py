from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from namel3ss.ast import nodes as ast
from namel3ss.lang.types import normalize_type_expression, split_union_members


UNKNOWN_TYPE = "unknown"


@dataclass(frozen=True)
class TypeIssue:
    code: str
    message: str
    suggestion: str
    line: int | None
    column: int | None
    severity: str = "error"

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
        }


def run_type_check(program: ast.Program) -> dict[str, object]:
    issues: list[TypeIssue] = []
    record_fields = _record_field_map(program, issues)
    _validate_declared_types(program, issues)
    flow_types = _infer_flow_return_types(program, record_fields, issues)
    route_checks = _validate_route_output_types(program, flow_types, issues)

    ordered = sorted(
        issues,
        key=lambda item: (
            item.line if isinstance(item.line, int) else 0,
            item.column if isinstance(item.column, int) else 0,
            item.code,
            item.message,
        ),
    )
    return {
        "ok": len([issue for issue in ordered if issue.severity == "error"]) == 0,
        "count": len(ordered),
        "issues": [issue.to_dict() for issue in ordered],
        "flow_types": {name: flow_types[name] for name in sorted(flow_types.keys())},
        "route_checks": route_checks,
    }


def _record_field_map(program: ast.Program, issues: list[TypeIssue]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for record in sorted(program.records, key=lambda item: item.name):
        fields: dict[str, str] = {}
        for field in sorted(record.fields, key=lambda item: item.name):
            normalized = _normalize_type(field.type_name, issues, line=field.line, column=field.column)
            fields[field.name] = normalized
        result[record.name] = fields
    return result


def _validate_declared_types(program: ast.Program, issues: list[TypeIssue]) -> None:
    for record in sorted(program.records, key=lambda item: item.name):
        for field in sorted(record.fields, key=lambda item: item.name):
            _normalize_type(field.type_name, issues, line=field.line, column=field.column)
    for route in sorted(program.routes, key=lambda item: item.name):
        _validate_route_fields(route.parameters or {}, issues)
        _validate_route_fields(route.request or {}, issues)
        _validate_route_fields(route.response or {}, issues)
    for function in sorted(program.functions, key=lambda item: item.name):
        for param in function.signature.inputs:
            _normalize_type(param.type_name, issues, line=param.line, column=param.column)
        for param in function.signature.outputs or []:
            _normalize_type(param.type_name, issues, line=param.line, column=param.column)


def _validate_route_fields(fields: dict[str, ast.RouteField], issues: list[TypeIssue]) -> None:
    for _name, field in sorted(fields.items(), key=lambda item: item[0]):
        _normalize_type(field.type_name, issues, line=field.line, column=field.column)


def _infer_flow_return_types(
    program: ast.Program,
    record_fields: dict[str, dict[str, str]],
    issues: list[TypeIssue],
) -> dict[str, str]:
    flow_map = {flow.name: flow for flow in program.flows}
    inferred: dict[str, str] = {}
    for flow in sorted(program.flows, key=lambda item: item.name):
        env: dict[str, str] = {}
        return_types: list[str] = []
        _infer_statements(flow.body, env, return_types, record_fields, issues)
        if not return_types:
            inferred[flow.name] = UNKNOWN_TYPE
            continue
        inferred[flow.name] = _merge_types(return_types)
    for flow_name in sorted(flow_map.keys()):
        inferred.setdefault(flow_name, UNKNOWN_TYPE)
    return inferred


def _infer_statements(
    statements: Iterable[ast.Statement],
    env: dict[str, str],
    return_types: list[str],
    record_fields: dict[str, dict[str, str]],
    issues: list[TypeIssue],
) -> None:
    for stmt in statements:
        if isinstance(stmt, ast.Let):
            inferred = _infer_expression_type(stmt.expression, env, record_fields, issues)
            env[stmt.name] = inferred
            if inferred == UNKNOWN_TYPE:
                issues.append(
                    TypeIssue(
                        code="type.infer_required",
                        message=f'Could not infer type for variable "{stmt.name}".',
                        suggestion="Add a clearer value or annotate through route/function schema.",
                        line=stmt.line,
                        column=stmt.column,
                    )
                )
            continue
        if isinstance(stmt, ast.Set):
            expected = _target_type(stmt.target, env)
            actual = _infer_expression_type(stmt.expression, env, record_fields, issues)
            if expected != UNKNOWN_TYPE and actual != UNKNOWN_TYPE and not _is_assignable(actual, expected):
                issues.append(
                    TypeIssue(
                        code="type.mismatch",
                        message=f"Cannot assign {actual} to {expected}.",
                        suggestion="Align the assigned value with the target type.",
                        line=stmt.line,
                        column=stmt.column,
                    )
                )
            continue
        if isinstance(stmt, ast.Return):
            return_types.append(_infer_expression_type(stmt.expression, env, record_fields, issues))
            continue
        if isinstance(stmt, ast.If):
            then_env = dict(env)
            else_env = dict(env)
            _infer_statements(stmt.then_body, then_env, return_types, record_fields, issues)
            _infer_statements(stmt.else_body, else_env, return_types, record_fields, issues)
            _merge_env_types(env, then_env, else_env)
            continue
        if isinstance(stmt, ast.ForEach):
            loop_env = dict(env)
            loop_env[stmt.name] = UNKNOWN_TYPE
            _infer_statements(stmt.body, loop_env, return_types, record_fields, issues)
            continue
        if isinstance(stmt, ast.Repeat):
            _infer_statements(stmt.body, dict(env), return_types, record_fields, issues)
            continue
        if isinstance(stmt, ast.Match):
            for case in stmt.cases:
                _infer_statements(case.body, dict(env), return_types, record_fields, issues)
            if stmt.otherwise:
                _infer_statements(stmt.otherwise, dict(env), return_types, record_fields, issues)
            continue


def _merge_env_types(target: dict[str, str], left: dict[str, str], right: dict[str, str]) -> None:
    for name in sorted(set(left.keys()) | set(right.keys())):
        values = [left.get(name, UNKNOWN_TYPE), right.get(name, UNKNOWN_TYPE)]
        target[name] = _merge_types(values)


def _target_type(target: ast.Assignable, env: dict[str, str]) -> str:
    if isinstance(target, ast.VarReference):
        return env.get(target.name, UNKNOWN_TYPE)
    return UNKNOWN_TYPE


def _infer_expression_type(
    expr: ast.Expression,
    env: dict[str, str],
    record_fields: dict[str, dict[str, str]],
    issues: list[TypeIssue],
) -> str:
    if isinstance(expr, ast.Literal):
        return _literal_type(expr.value)
    if isinstance(expr, ast.VarReference):
        return env.get(expr.name, UNKNOWN_TYPE)
    if isinstance(expr, ast.AttrAccess):
        base = env.get(expr.base, UNKNOWN_TYPE)
        if base in record_fields and expr.attrs:
            return record_fields[base].get(expr.attrs[-1], UNKNOWN_TYPE)
        return UNKNOWN_TYPE
    if isinstance(expr, ast.StatePath):
        return UNKNOWN_TYPE
    if isinstance(expr, ast.UnaryOp):
        return _infer_expression_type(expr.operand, env, record_fields, issues)
    if isinstance(expr, ast.BinaryOp):
        left = _infer_expression_type(expr.left, env, record_fields, issues)
        right = _infer_expression_type(expr.right, env, record_fields, issues)
        return _binary_type(expr.op, left, right)
    if isinstance(expr, ast.Comparison):
        return "boolean"
    if isinstance(expr, ast.ListExpr):
        values = [_infer_expression_type(item, env, record_fields, issues) for item in expr.items]
        item_type = _merge_types(values)
        return f"list<{item_type}>"
    if isinstance(expr, ast.MapExpr):
        values = [_infer_expression_type(item.value, env, record_fields, issues) for item in expr.entries]
        value_type = _merge_types(values)
        return f"map<text, {value_type}>"
    if isinstance(expr, ast.CallFlowExpr):
        return UNKNOWN_TYPE
    if isinstance(expr, ast.CallFunctionExpr):
        return UNKNOWN_TYPE
    if isinstance(expr, ast.CallPipelineExpr):
        return UNKNOWN_TYPE
    if isinstance(expr, ast.ListMapExpr):
        return f"list<{_infer_expression_type(expr.body, env, record_fields, issues)}>"
    if isinstance(expr, ast.ListFilterExpr):
        base_type = _infer_expression_type(expr.target, env, record_fields, issues)
        return base_type if base_type.startswith("list<") else "list<unknown>"
    if isinstance(expr, ast.ListReduceExpr):
        return _infer_expression_type(expr.body, env, record_fields, issues)
    if isinstance(expr, ast.ListOpExpr):
        if expr.kind == "length":
            return "number"
        if expr.kind == "get":
            target_type = _infer_expression_type(expr.target, env, record_fields, issues)
            if target_type.startswith("list<") and target_type.endswith(">"):
                return target_type[5:-1]
        return UNKNOWN_TYPE
    if isinstance(expr, ast.MapOpExpr):
        if expr.kind == "keys":
            return "list<text>"
        if expr.kind == "get":
            target_type = _infer_expression_type(expr.target, env, record_fields, issues)
            if target_type.startswith("map<") and target_type.endswith(">"):
                body = target_type[4:-1]
                parts = [part.strip() for part in body.split(",", 1)]
                if len(parts) == 2:
                    return parts[1]
        return UNKNOWN_TYPE
    return UNKNOWN_TYPE


def _binary_type(op: str, left: str, right: str) -> str:
    if op in {"and", "or"}:
        return "boolean"
    if op == "+":
        if left == "number" and right == "number":
            return "number"
        if left == "text" or right == "text":
            return "text"
        return _merge_types([left, right])
    if op in {"-", "*", "/", "%"}:
        if left == "number" and right == "number":
            return "number"
        return UNKNOWN_TYPE
    return _merge_types([left, right])


def _literal_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float, Decimal)):
        return "number"
    if isinstance(value, str):
        return "text"
    return UNKNOWN_TYPE


def _merge_types(values: Iterable[str]) -> str:
    normalized: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        if text == UNKNOWN_TYPE:
            continue
        members = split_union_members(text)
        for item in members:
            if item not in normalized:
                normalized.append(item)
    if not normalized:
        return UNKNOWN_TYPE
    if len(normalized) == 1:
        return normalized[0]
    return " | ".join(sorted(normalized))


def _is_assignable(actual: str, expected: str) -> bool:
    if actual == UNKNOWN_TYPE or expected == UNKNOWN_TYPE:
        return True
    try:
        normalized_expected, _ = normalize_type_expression(expected)
        normalized_actual, _ = normalize_type_expression(actual)
    except Exception:
        return False
    expected_set = set(split_union_members(normalized_expected))
    actual_set = set(split_union_members(normalized_actual))
    if "json" in expected_set:
        return True
    if actual_set.issubset(expected_set):
        return True
    if normalized_expected == normalized_actual:
        return True
    return False


def _normalize_type(type_name: str, issues: list[TypeIssue], *, line: int | None, column: int | None) -> str:
    try:
        normalized, _ = normalize_type_expression(type_name)
        return normalized
    except Exception as err:
        issues.append(
            TypeIssue(
                code="type.invalid",
                message=f"Invalid type expression '{type_name}': {err}",
                suggestion="Use names like text, number, list<text>, map<text, number>, or text | null.",
                line=line,
                column=column,
            )
        )
        return type_name


def _validate_route_output_types(
    program: ast.Program,
    flow_types: dict[str, str],
    issues: list[TypeIssue],
) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for route in sorted(program.routes, key=lambda item: item.name):
        if not route.response:
            continue
        if len(route.response) != 1:
            checks.append(
                {
                    "route": route.name,
                    "status": "skipped",
                    "reason": "multi_field_response",
                }
            )
            continue
        response_field = next(iter(route.response.values()))
        expected = _normalize_type(response_field.type_name, issues, line=response_field.line, column=response_field.column)
        actual = flow_types.get(route.flow_name, UNKNOWN_TYPE)
        ok = _is_assignable(actual, expected)
        checks.append(
            {
                "route": route.name,
                "flow": route.flow_name,
                "expected": expected,
                "actual": actual,
                "ok": ok,
            }
        )
        if not ok:
            issues.append(
                TypeIssue(
                    code="type.route_response_mismatch",
                    message=f'Route "{route.name}" expects {expected} but flow "{route.flow_name}" returns {actual}.',
                    suggestion="Update the response schema or return value.",
                    line=route.line,
                    column=route.column,
                )
            )
    return checks


__all__ = ["run_type_check"]
