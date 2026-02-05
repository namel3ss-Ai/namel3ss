from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.lint.types import Finding


_ROUTE_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_ROUTE_TYPES = {"text", "number", "boolean", "json"}


def lint_routes(
    ast_program,
    *,
    strict: bool,
    flow_names: set[str] | None = None,
    record_names: set[str] | None = None,
) -> list[Finding]:
    routes = list(getattr(ast_program, "routes", []) or [])
    if not routes:
        return []
    if flow_names is None:
        flow_names = {flow.name for flow in getattr(ast_program, "flows", [])}
    if record_names is None:
        record_names = {record.name for record in getattr(ast_program, "records", [])}
    contract_names = {contract.name for contract in getattr(ast_program, "contracts", [])}
    ai_flow_names = {flow.name for flow in getattr(ast_program, "ai_flows", [])}
    findings: list[Finding] = []
    seen: set[str] = set()
    for route in routes:
        if route.name in seen:
            findings.append(
                Finding(
                    code="routes.duplicate_name",
                    message=f"Route '{route.name}' is declared more than once.",
                    line=route.line,
                    column=route.column,
                    severity="error",
                )
            )
        else:
            seen.add(route.name)
        if not route.path:
            findings.append(
                Finding(
                    code="routes.missing_path",
                    message="Route is missing a path.",
                    line=route.line,
                    column=route.column,
                    severity="error",
                )
            )
        if not route.method:
            findings.append(
                Finding(
                    code="routes.missing_method",
                    message="Route is missing a method.",
                    line=route.line,
                    column=route.column,
                    severity="error",
                )
            )
        elif str(route.method).upper() not in _ROUTE_METHODS:
            findings.append(
                Finding(
                    code="routes.invalid_method",
                    message="Route method must be GET, POST, PUT, PATCH, or DELETE.",
                    line=route.line,
                    column=route.column,
                    severity="error",
                )
            )
        if not route.response:
            findings.append(
                Finding(
                    code="routes.missing_response",
                    message="Route is missing a response block.",
                    line=route.line,
                    column=route.column,
                    severity="error",
                )
            )
        if not route.request:
            findings.append(
                Finding(
                    code="routes.missing_request",
                    message="Route is missing a request block.",
                    line=route.line,
                    column=route.column,
                    severity="error",
                )
            )
        if not route.flow_name:
            findings.append(
                Finding(
                    code="routes.missing_flow",
                    message="Route is missing a flow.",
                    line=route.line,
                    column=route.column,
                    severity="error",
                )
            )
        elif route.flow_name not in flow_names:
            findings.append(
                Finding(
                    code="routes.unknown_flow",
                    message=f"Route references unknown flow '{route.flow_name}'.",
                    line=route.line,
                    column=route.column,
                    severity="error",
                )
            )
        elif route.flow_name not in contract_names and route.flow_name not in ai_flow_names:
            findings.append(
                Finding(
                    code="routes.missing_flow_contract",
                    message=f'Route flow "{route.flow_name}" is missing a contract.',
                    line=route.line,
                    column=route.column,
                    severity="error",
                )
            )
        findings.extend(_lint_route_fields(route.parameters or {}, record_names, strict=strict))
        if route.request:
            findings.extend(_lint_route_fields(route.request, record_names, strict=strict))
        if route.response:
            findings.extend(_lint_route_fields(route.response, record_names, strict=strict))
            list_fields = _list_response_fields(route.response)
            if list_fields:
                next_page = route.response.get("next_page")
                if next_page is None:
                    findings.append(
                        Finding(
                            code="routes.missing_next_page",
                            message="Route list responses must include next_page.",
                            line=route.line,
                            column=route.column,
                            severity="error",
                        )
                    )
                elif getattr(next_page, "type_name", None) != "number":
                    findings.append(
                        Finding(
                            code="routes.next_page_type",
                            message="next_page must be a number.",
                            line=getattr(next_page, "type_line", route.line),
                            column=getattr(next_page, "type_column", route.column),
                            severity="error",
                        )
                    )
    return findings


def _lint_route_fields(
    fields: dict[str, ast.RouteField],
    record_names: set[str],
    *,
    strict: bool,
) -> list[Finding]:
    severity = "error" if strict else "warning"
    findings: list[Finding] = []
    for field in fields.values():
        if getattr(field, "type_was_alias", False) and field.raw_type_name:
            findings.append(
                Finding(
                    code="N3LINT_TYPE_NON_CANONICAL",
                    message=f"Use `{field.type_name}` instead of `{field.raw_type_name}` for route types.",
                    line=field.type_line,
                    column=field.type_column,
                    severity=severity,
                )
            )
        if not _route_type_valid(field.type_name, record_names):
            findings.append(
                Finding(
                    code="routes.unknown_type",
                    message=f"Unsupported route type '{field.type_name}'.",
                    line=field.type_line,
                    column=field.type_column,
                    severity="error",
                )
            )
    return findings


def _route_type_valid(type_name: str, record_names: set[str]) -> bool:
    if not isinstance(type_name, str) or not type_name:
        return False
    inner = _split_list_type(type_name)
    if inner is not None:
        return _route_type_valid(inner, record_names)
    if type_name in _ROUTE_TYPES:
        return True
    return type_name in record_names


def _split_list_type(type_name: str) -> str | None:
    if not type_name.startswith("list<"):
        return None
    depth = 0
    start = None
    end = None
    for idx, ch in enumerate(type_name):
        if ch == "<":
            depth += 1
            if depth == 1:
                start = idx + 1
        elif ch == ">":
            depth -= 1
            if depth == 0:
                end = idx
                break
    if start is None or end is None or end != len(type_name) - 1:
        return None
    inner = type_name[start:end].strip()
    if not inner:
        return None
    return inner


def _list_response_fields(fields: dict[str, ast.RouteField]) -> list[str]:
    names: list[str] = []
    for name, field in fields.items():
        if isinstance(field.type_name, str) and field.type_name.startswith("list<"):
            names.append(name)
    return names


__all__ = ["lint_routes"]
